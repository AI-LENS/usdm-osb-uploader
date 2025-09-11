import re
from collections import defaultdict

import httpx
from pydantic import BaseModel

from ..settings import settings
from .osb_api import (
    create_study_activity_schedule,
    create_study_structure_study_epoch,
    create_study_structure_study_visit,
)


class StudyActivity(BaseModel):
    """Study activity model from API response."""

    study_activity_uid: str
    activity_name: str
    activity_uid: str
    order: int


def extract_day_or_week_value_dynamic_with_anchor_flag(timings: list) -> dict:
    anchor_found = False
    results = {}

    for timing in timings:
        enc_id = timing.get("encounterId")
        label = (timing.get("label") or "").lower()
        value_label = (timing.get("valueLabel") or "").strip().lower()
        description = (timing.get("description") or "").lower()

        if "anchor" in description:
            anchor_found = True
            results[enc_id] = (0, "day")
            continue

        day_match = re.search(r"day\s*(-?\d+)", label)
        week_match = re.search(r"week\s*(-?\d+)", label)

        if day_match:
            val = int(day_match.group(1))
            results[enc_id] = (val if anchor_found else -abs(val), "day")
            continue
        elif week_match:
            val = int(week_match.group(1))
            results[enc_id] = (val if anchor_found else -abs(val), "week")
            continue

        val_match = re.search(r"-?\d+", value_label)
        if val_match:
            val = int(val_match.group(0))
            unit = "week" if "week" in label or "week" in value_label else "day"
            results[enc_id] = (val if anchor_found else -abs(val), unit)
        else:
            results[enc_id] = (None, None)

    return results


def finalize_timing_integration(schedule: dict, encounters: list) -> dict:
    instances = schedule.get("instances", [])
    timings = schedule.get("timings", [])

    inst_to_enc = {
        inst.get("id"): inst.get("encounterId")
        for inst in instances
        if inst.get("encounterId")
    }

    for timing in timings:
        rel_id = timing.get("relativeFromScheduledInstanceId")
        mapped_enc_id = inst_to_enc.get(rel_id)
        timing["encounterId"] = mapped_enc_id

    valid_timings = [t for t in timings if t.get("encounterId")]
    anchor_based_timing_map = extract_day_or_week_value_dynamic_with_anchor_flag(
        valid_timings
    )

    result = {}
    for enc in encounters:
        enc_id = enc.get("id")
        val, unit = anchor_based_timing_map.get(enc_id, (None, None))
        if val is not None and unit:
            result[enc_id] = {"value": val, "unit": unit}
    return result


async def fetch_contact_mode_uid(decode_value: str) -> str:
    decode_map = {"In person": "On Site Visit", "Telephone call": "Phone Contact"}
    preferred_name = decode_map.get(decode_value)
    if not preferred_name:
        return None
    url = f"{settings.osb_base_url}/api/ct/terms?codelist_name=Visit%20Contact%20Mode&is_sponsor=false&page_number=1&page_size=100"
    headers = {"accept": "application/json, text/plain, */*"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            for item in response.json().get("items", []):
                name = item.get("name", {}).get("sponsor_preferred_name", "")
                if name == preferred_name:
                    return item.get("term_uid")
    return None


async def fetch_existing_study_activities(study_uid: str):
    """
    Fetch existing study activities from the API.

    Returns a list of study activities with their UIDs and names.
    """
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-activities"
    params = {"page_size": 0, "page_number": 1}

    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()

    activities = []

    for item in data.get("items", []):
        activity_data = StudyActivity(
            study_activity_uid=item.get("study_activity_uid"),
            activity_name=item.get("activity", {}).get("name", ""),
            activity_uid=item.get("activity", {}).get("uid", ""),
            order=item.get("order", 0),
        )
        activities.append(activity_data)

    return activities


async def create_epochs_visits_soa(study_designs: list, study_uid: str):
    epoch_uid_map = {}
    visit_mapping_encounter = {}
    epochs = study_designs[0].get("epochs", [])
    elements = study_designs[0].get("elements", [])
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.osb_base_url}/epochs/allowed-configs")
        if response.status_code == 200:
            allowed_configs = response.json()
            # print(allowed_configs)
    for index, epoc in enumerate(epochs):
        epoch_id = epoc.get("id")
        epoch_order = index
        description = epoc.get("description", "")
        label = epoc.get("name", "")  # noqa: F841
        idx = next(
            (
                i
                for i, elem in enumerate(elements)
                if elem.get("id")[-1] == epoch_id[-1]
            ),
            None,
        )
        if idx is not None:
            start_rule_dict = elements[idx].get("transitionStartRule")
            start_rule = start_rule_dict.get("text") if start_rule_dict else None
            end_rule_dict = elements[idx].get("transitionEndRule")
            end_rule = end_rule_dict.get("text") if end_rule_dict else None
        else:
            start_rule = None
            end_rule = None

        if label.lower() == "screening":
            epoch_type_codes = "C48262"
        elif label.lower() == "follow-up":
            epoch_type_codes = "C99158"
        else:
            epoch_type_codes = epoc.get("type", {}).get("code", "")

        if epoch_type_codes:
            headers = {"accept": "application/json, text/plain, */*"}
            async with httpx.AsyncClient() as client:
                epochs_codelist = await client.get(
                    f"{settings.osb_base_url}/ct/terms?codelist_uid=C99079&page_number=1&page_size=1000",
                    headers=headers,
                )
                if epochs_codelist.status_code == 200:
                    items = epochs_codelist.json().get("items", [])
                    grouped_epochs = defaultdict(list)
                    for epoc in allowed_configs:
                        try:
                            term = next(
                                term
                                for term in epochs_codelist.json().get("items", [])
                                if term.get("term_uid") == epoc.get("subtype")
                            )
                            definition = term.get("attributes", {}).get(
                                "definition", ""
                            )
                            grouped_epochs[epoc.get("type_name")].append({
                                "type": epoc.get("type"),
                                "type_name": epoc.get("type_name"),
                                "subtype": epoc.get("subtype"),
                                "subtype_name": epoc.get("subtype_name"),
                                "definition": definition,
                            })
                        except StopIteration:
                            pass

                    all_subtypes = [
                        item for sub_tps in grouped_epochs.values() for item in sub_tps
                    ]
                    for item in items:
                        if (
                            item.get("attributes", {}).get("concept_id", "")
                            == epoch_type_codes
                        ):
                            epoch_subtype = item.get("term_uid", "")
                            sponsor_name = (
                                item.get("name", {})
                                .get("sponsor_preferred_name", "")
                                .lower()
                            )
                            matching_cfg = next(
                                (
                                    cfg
                                    for cfg in all_subtypes
                                    if cfg["type_name"] == sponsor_name
                                ),
                                None,
                            )
                            # print(matching_cfg)
                            epoch_type = matching_cfg["type"] if matching_cfg else None

                            epochs_response = await create_study_structure_study_epoch(
                                study_uid=study_uid,
                                epoch_type=epoch_type,
                                epoch_subtype=epoch_subtype,
                                start_rule=start_rule,
                                end_rule=end_rule,
                                order=epoch_order + 1,
                                description=description,
                            )
                            epoch_uid_map[epoch_id] = epochs_response.get("uid")

    print("Epochs created successfully.")
    design = study_designs[0]
    encounters = design.get("encounters", [])
    schedule = design.get("scheduleTimelines", [])[0]

    encounter_timing_map = finalize_timing_integration(schedule, encounters)
    epoch_first_visit_flag = defaultdict(lambda: True)

    first_unit = None
    for timing_data in encounter_timing_map.values():
        if timing_data.get("unit") in ["day", "week"]:
            first_unit = timing_data["unit"]
            break

    global_visit_window_unit_uid = (  # noqa: F841
        "UnitDefinition_000364"
        if first_unit == "day"
        else "UnitDefinition_000368"
        if first_unit == "week"
        else "UnitDefinition_000364"
    )

    # Sort encounters by time value to ensure proper chronological order
    encounter_time_pairs = []
    for enc in encounters:
        enc_id = enc.get("id")
        timing_data = encounter_timing_map.get(enc_id, {})
        time_val = timing_data.get("value")
        if time_val is not None:
            encounter_time_pairs.append((time_val, enc))
        else:
            encounter_time_pairs.append((float("inf"), enc))

    encounter_time_pairs.sort(key=lambda x: x[0])

    for time_val, enc in encounter_time_pairs:
        enc_id = enc.get("id")
        epoch_id = next(
            (
                inst.get("epochId")
                for inst in schedule["instances"]
                if inst.get("encounterId") == enc_id
            ),
            None,
        )
        epoch_uid = epoch_uid_map.get(epoch_id)
        if not epoch_uid:
            continue

        timing_data = encounter_timing_map.get(enc_id, {})
        time_val = timing_data.get("value")
        if time_val == 0:
            unit = timing_data.get("unit")
            if unit == "week":
                time_value_in_days = time_val * 7
            else:
                time_value_in_days = time_val

            time_unit_uid = "UnitDefinition_000364"

            description = enc.get("description", "")
            label = enc.get("label", "").lower()
            if "screening" in label:
                visit_type_uid = "CTTerm_000186"
            elif "pre-screening" in label:
                visit_type_uid = "CTTerm_000184"
            elif "follow up" in label or "follow-up" in label:
                visit_type_uid = "CTTerm_000182"
            elif "washout" in label or "wash out" in label:
                visit_type_uid = "CTTerm_000192"
            elif "treatment" in label:
                visit_type_uid = "CTTerm_000191"
            elif "pre-treatment" in label:
                visit_type_uid = "CTTerm_000181"
            elif "no-treatment" in label:
                visit_type_uid = "CTTerm_000194"
            elif "randomisation" in label:
                visit_type_uid = "CTTerm_000183"
            elif "run-in" in label or "check in" in label:
                visit_type_uid = "CTTerm_000188"
            elif "surgery" in label:
                visit_type_uid = "CTTerm_000189"
            else:
                visit_type_uid = "CTTerm_000190"

            contact_modes = enc.get("contactModes", [])
            contact_mode_decode = (
                contact_modes[0].get("decode") if contact_modes else ""
            )
            contact_mode_uid = (
                await fetch_contact_mode_uid(decode_value=contact_mode_decode)
                or "CTTerm_000082"
            )

            is_milestone = epoch_first_visit_flag[epoch_uid]
            epoch_first_visit_flag[epoch_uid] = False

            try:
                create_response = await create_study_structure_study_visit(
                    study_uid=study_uid,
                    is_global_anchor_visit=time_val == 0,
                    study_epoch_uid=epoch_uid,
                    visit_type_uid=visit_type_uid,
                    visit_contact_mode_uid=contact_mode_uid,
                    time_value=time_value_in_days,
                    time_unit_uid=time_unit_uid,
                    description=description,
                )
                visit_mapping_encounter[enc_id] = create_response.get("uid")
            except Exception as e:
                print(f"Error creating visit {enc.get('label', enc_id)}: {str(e)}")
        else:
            continue

    for time_val, enc in encounter_time_pairs:
        enc_id = enc.get("id")
        epoch_id = next(
            (
                inst.get("epochId")
                for inst in schedule["instances"]
                if inst.get("encounterId") == enc_id
            ),
            None,
        )
        epoch_uid = epoch_uid_map.get(epoch_id)
        if not epoch_uid:
            continue

        timing_data = encounter_timing_map.get(enc_id, {})
        time_val = timing_data.get("value")

        if time_val != 0:
            unit = timing_data.get("unit")
            if unit == "week":
                time_value_in_days = time_val * 7
            else:
                time_value_in_days = time_val

            time_unit_uid = "UnitDefinition_000364"

            description = enc.get("description", "")
            label = enc.get("label", "").lower()
            if "screening" in label:
                visit_type_uid = "CTTerm_000186"
            elif "pre-screening" in label:
                visit_type_uid = "CTTerm_000184"
            elif "follow up" in label or "follow-up" in label:
                visit_type_uid = "CTTerm_000182"
            elif "washout" in label or "wash out" in label:
                visit_type_uid = "CTTerm_000192"
            elif "treatment" in label:
                visit_type_uid = "CTTerm_000191"
            elif "pre-treatment" in label:
                visit_type_uid = "CTTerm_000181"
            elif "no-treatment" in label:
                visit_type_uid = "CTTerm_000194"
            elif "randomisation" in label:
                visit_type_uid = "CTTerm_000183"
            elif "run-in" in label or "check in" in label:
                visit_type_uid = "CTTerm_000188"
            elif "surgery" in label:
                visit_type_uid = "CTTerm_000189"
            else:
                visit_type_uid = "CTTerm_000190"

            contact_modes = enc.get("contactModes", [])
            contact_mode_decode = (
                contact_modes[0].get("decode") if contact_modes else ""
            )
            contact_mode_uid = (
                await fetch_contact_mode_uid(decode_value=contact_mode_decode)
                or "CTTerm_000082"
            )

            is_milestone = epoch_first_visit_flag[epoch_uid]  # noqa: F841
            epoch_first_visit_flag[epoch_uid] = False

            try:
                create_response = await create_study_structure_study_visit(  # noqa: F841
                    study_uid=study_uid,
                    is_global_anchor_visit=time_value_in_days == 0,
                    study_epoch_uid=epoch_uid,
                    visit_type_uid=visit_type_uid,
                    visit_contact_mode_uid=contact_mode_uid,
                    time_value=time_value_in_days,
                    time_unit_uid=time_unit_uid,
                    description=description,
                )
                visit_mapping_encounter[enc_id] = create_response.get("uid")
            except Exception as e:
                print(f"Error creating visit {enc.get('label', enc_id)}: {str(e)}")
        else:
            continue

    print("Visits created successfully.")

    design = study_designs[0]
    schedule = design.get("scheduleTimelines", [])[0]
    instances = schedule.get("instances", [])
    activities = await fetch_existing_study_activities(study_uid=study_uid)

    for instance in instances:
        enc_id = instance.get("encounterId")
        visit_id = visit_mapping_encounter.get(enc_id)
        if not visit_id:
            continue
        for act_id in instance.get("activityIds", []):
            activity = next(
                (
                    a
                    for a in activities
                    if a.activity_name.lower()
                    == (
                        next(
                            (
                                act
                                for act in design.get("activities", [])
                                if act.get("id") == act_id
                            ),
                            {},
                        ).get("name")
                        or ""
                    ).lower()
                ),
                None,
            )
            if activity is None:
                continue
            try:
                await create_study_activity_schedule(
                    study_uid=study_uid,
                    study_activity_uid=activity.study_activity_uid,
                    study_visit_uid=visit_id,
                )
            except Exception as e:
                print(
                    f"Error creating schedule of activity for activity {activity.activity_name} and visit {visit_id}: {str(e)}"
                )

    print("Schedule of activities created successfully.")
    print("Study epochs, visits and schedule of activities created successfully.")
