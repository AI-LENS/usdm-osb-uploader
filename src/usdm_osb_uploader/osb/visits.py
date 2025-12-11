import re
from collections import defaultdict

import httpx

from ..settings import settings
from .osb_api import create_study_structure_study_visit


def extract_day_or_week_value_dynamic_with_anchor_flag(timings: list) -> dict:
    anchor_found = False
    results = {}

    for timing in timings:
        enc_id = timing.get("encounterId")
        value_label = (timing.get("valueLabel") or "").strip().lower()
        description = (timing.get("description") or "").lower()

        if results.get(enc_id):
            continue

        if "anchor" in description:
            anchor_found = True
            results[enc_id] = (0, "day")
            continue

        day_match = re.search(r"(?:day\s*(-?\d+)|(-?\d+)\s*days?)", value_label)
        week_match = re.search(r"(?:week\s*(-?\d+)|(-?\d+)\s*weeks?)", value_label)

        if day_match:
            val = int(day_match.group(1) or day_match.group(2))
            results[enc_id] = (val if anchor_found else -abs(val), "day")
            continue
        elif week_match:
            val = int(week_match.group(1) or week_match.group(2))
            results[enc_id] = (val if anchor_found else -abs(val), "week")
            continue

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


async def fetch_contact_mode_uid(code_value: str) -> str:
    code_map = {"C175574": "On Site Visit", "C171537": "Phone Contact"}
    for key, value in code_map.items():
        if key.lower() == code_value.lower():
            preferred_name = value
            break

    if not preferred_name:
        return None
    headers = {"accept": "application/json, text/plain, */*"}
    async with httpx.AsyncClient() as client:
        res = await client.get(
            (settings.osb_base_url)
            + "/ct/codelists?filters=%7B%22*%22:%7B%22v%22:%5B%22visit+contact+mode%22%5D%7D%7D&library_name=Sponsor"
        )
        res.raise_for_status()
        data = res.json()
        contact_type_ct_uid = data.get("items", [])[0].get("codelist_uid")

        response = await client.get(
            f"{settings.osb_base_url}/ct/terms?codelist_uid={contact_type_ct_uid}&page_number=1&page_size=1000",
            headers=headers,
        )
        if response.status_code == 200:
            for item in response.json().get("items", []):
                name = item.get("name", {}).get("sponsor_preferred_name", "")
                if name == preferred_name:
                    return item.get("term_uid")


async def create_study_visits(study_designs: list, study_uid: str):
    design = study_designs[0]
    epochs = study_designs[0].get("epochs", [])
    encounters = design.get("encounters", [])
    schedule = design.get("scheduleTimelines", [])[0]

    encounter_timing_map = finalize_timing_integration(schedule, encounters)
    epoch_first_visit_flag = defaultdict(lambda: True)
    print(encounter_timing_map)

    first_unit = None
    for timing_data in encounter_timing_map.values():
        if timing_data.get("unit") in ["day", "week"]:
            first_unit = timing_data["unit"]
            break

    global_visit_window_unit_uid = ""
    time_unit_response = None
    async with httpx.AsyncClient() as client:
        time_unit_response = await client.get(
            "https://dev-osb.ailens.ai/api/concepts/unit-definitions?subset=Study+Time&sort_by[conversion_factor_to_master]=true&page_size=0"
        )
        for item in time_unit_response.json().get("items", []):
            if item.get("name") == first_unit:
                global_visit_window_unit_uid = item.get("uid")
                break

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

    async with httpx.AsyncClient() as client:
        epochs_response = await client.get(
            f"{settings.osb_base_url}/studies/{study_uid}/study-epochs?page_number=1&page_size=10&total_count=true&study_uid={study_uid}"
        )

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

        epoch_name: str = ""
        epoch_uid: str = ""
        epoch_type_name: str = ""
        visit_type_uid: str = ""

        for epoch in epochs:
            if epoch.get("id") == epoch_id:
                epoch_name = epoch.get("name", "")
                break

        for item in epochs_response.json().get("items", []):
            if item.get("epoch_name", "") == epoch_name:
                epoch_uid = item.get("uid", "")
                epoch_type_name = item.get("epoch_subtype_name", "")
                break
        async with httpx.AsyncClient() as client:
            visit_type_response = await client.get(
                f"{settings.osb_base_url}/ct/terms/names?page_size=0&codelist_name=VisitType"
            )
            for item in visit_type_response.json().get("items", []):
                if (
                    item.get("sponsor_preferred_name", "").lower()
                    == epoch_type_name.lower()
                ):
                    visit_type_uid = item.get("term_uid")
                    break
        if not epoch_uid:
            continue

        timing_data = encounter_timing_map.get(enc_id, {})
        time_val = timing_data.get("value")
        if time_val == 0:
            time_unit_uid = ""
            for item in time_unit_response.json().get("items", []):
                if item.get("name") == timing_data.get("unit"):
                    time_unit_uid = item.get("uid")
                    break

            description = enc.get("description", "")
            label = enc.get("label", "").lower()  # noqa: F841

            contact_modes = enc.get("contactModes", [])
            contact_mode_code = contact_modes[0].get("code") if contact_modes else ""
            contact_mode_uid = await fetch_contact_mode_uid(
                code_value=contact_mode_code
            )

            is_milestone = epoch_first_visit_flag[epoch_uid]
            epoch_first_visit_flag[epoch_uid] = False

            try:
                create_response = await create_study_structure_study_visit(
                    study_uid=study_uid,
                    study_epoch_uid=epoch_uid,
                    visit_type_uid=visit_type_uid,
                    visit_contact_mode_uid=contact_mode_uid,
                    time_value=time_val,
                    time_unit_uid=time_unit_uid,
                    visit_window_unit_uid=global_visit_window_unit_uid,
                    is_global_anchor_visit=time_val == 0,
                    description=description,
                )
                # visit_mapping_encounter[enc_id] = create_response.get("uid")
            except Exception as e:
                if (
                    isinstance(e, httpx.HTTPStatusError)
                    and e.response.status_code == 409
                ):
                    print(f"Visit {enc.get('label', enc_id)} already exists")
                else:
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

        epoch_name: str = ""
        epoch_uid: str = ""
        epoch_type_name: str = ""
        visit_type_uid: str = ""

        for epoch in epochs:
            if epoch.get("id") == epoch_id:
                epoch_name = epoch.get("name", "")
                break
        for item in epochs_response.json().get("items", []):
            if item.get("epoch_name", "") == epoch_name:
                epoch_uid = item.get("uid", "")
                epoch_type_name = item.get("epoch_subtype_name", "")
                break
        async with httpx.AsyncClient() as client:
            visit_type_response = await client.get(
                f"{settings.osb_base_url}/ct/terms/names?page_size=0&codelist_name=VisitType"
            )
            for item in visit_type_response.json().get("items", []):
                if (
                    item.get("sponsor_preferred_name", "").lower()
                    == epoch_type_name.lower()
                ):
                    visit_type_uid = item.get("term_uid")
                    break
        if not epoch_uid:
            continue

        timing_data = encounter_timing_map.get(enc_id, {})
        time_val = timing_data.get("value")
        if time_val != 0:
            time_unit_uid = ""
            for item in time_unit_response.json().get("items", []):
                if item.get("name") == timing_data.get("unit"):
                    time_unit_uid = item.get("uid")
                    break

            description = enc.get("description", "")

            contact_modes = enc.get("contactModes", [])
            contact_mode_code = contact_modes[0].get("code") if contact_modes else ""
            contact_mode_uid = await fetch_contact_mode_uid(
                code_value=contact_mode_code
            )

            is_milestone = epoch_first_visit_flag[epoch_uid]  # noqa: F841
            epoch_first_visit_flag[epoch_uid] = False

            try:
                create_response = await create_study_structure_study_visit(  # noqa: F841
                    study_uid=study_uid,
                    study_epoch_uid=epoch_uid,
                    visit_type_uid=visit_type_uid,
                    visit_contact_mode_uid=contact_mode_uid,
                    time_value=time_val,
                    time_unit_uid=time_unit_uid,
                    visit_window_unit_uid=global_visit_window_unit_uid,
                    is_global_anchor_visit=time_val == 0,
                    description=description,
                )
                # visit_mapping_encounter[enc_id] = create_response.get("uid")
            except Exception as e:
                if (
                    isinstance(e, httpx.HTTPStatusError)
                    and e.response.status_code == 409
                ):
                    print(f"Visit {enc.get('label', enc_id)} already exists")
                else:
                    print(f"Error creating visit {enc.get('label', enc_id)}: {str(e)}")
        else:
            continue

    print("Visits created successfully.")
