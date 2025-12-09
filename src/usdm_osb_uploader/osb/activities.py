from difflib import get_close_matches

import httpx

from ..settings import settings
from .osb_api import (
    create_study_activities_approvals,
    create_study_activities_batch,
    create_study_activities_concept,
)


async def search_frontend_activity(name):
    headers = {"accept": "application/json, text/plain, */*"}
    endpoint = f"{settings.osb_base_url}/concepts/activities/activities?page_number=1&page_size=1000"
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, headers=headers)
        if response.status_code != 200:
            return None
        items = response.json().get("items", [])
        match = get_close_matches(
            name.lower(), [i.get("name", "").lower() for i in items], n=1, cutoff=0.6
        )
        if match:
            for i in items:
                if i.get("name", "").lower() == match[0]:
                    return i
        return None


async def get_or_create_group(group_name):
    clean_name = group_name.lower().replace("grouping activity", "").strip()
    target_name = group_name.upper() if clean_name.startswith("tbd") else clean_name
    headers = {"accept": "application/json, text/plain, */*"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.osb_base_url}/concepts/activities/activity-groups?page_number=1&page_size=1000",
            headers=headers,
        )
        response.raise_for_status()
        groups = response.json().get("items", [])

        for group in groups:
            if group.get("name", "").lower().strip() == target_name.lower().strip():
                group_uid = group.get("uid")
                return group_uid
        else:
            payload = {
                "name": target_name,
                "name_sentence_case": clean_name.lower(),
                "definition": f"Auto-generated group for {clean_name}",
                "abbreviation": clean_name[:3].upper(),
                "library_name": "Requested",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.osb_base_url}/concepts/activities/activity-groups",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 422:
                    print(f"Failed to create group '{target_name}': {response.text}")
                    return None
                response.raise_for_status()
                group_uid = response.json().get("uid")
                try:
                    await client.post(
                        f"{settings.osb_base_url}/concepts/activities/activity-groups/{group_uid}/approvals?cascade=false",
                        headers=headers,
                    )
                except Exception as e:
                    print(f"Failed to approve group {group_uid}: {e}")
                return group_uid


async def get_or_create_subgroup(subgroup_name, group_uid):
    clean_name = subgroup_name.lower().replace("grouping activity", "").strip()
    target_name = subgroup_name.upper() if clean_name.startswith("tbd") else clean_name
    headers = {"accept": "application/json, text/plain, */*"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.osb_base_url}/concepts/activities/activity-sub-groups?page_number=1&page_size=1000",
            headers=headers,
        )
        response.raise_for_status()
        subgroups = response.json().get("items", [])

        for sg in subgroups:
            name = sg.get("name", "").lower().strip()
            if name == target_name.lower().strip():
                subgroup_uid = sg.get("uid")
                return subgroup_uid
        else:
            payload = {
                "name": target_name,
                "name_sentence_case": clean_name.lower(),
                "definition": f"Auto-generated subgroup for {clean_name}",
                "abbreviation": clean_name[:3].upper(),
                "library_name": "Requested",
                "activity_groups": [group_uid],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.osb_base_url}/concepts/activities/activity-sub-groups",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 422:
                    print(f"Failed to create subgroup '{target_name}': {response.text}")
                    return None
                response.raise_for_status()
                subgroup_uid = response.json().get("uid")
                try:
                    await client.post(
                        f"{settings.osb_base_url}/concepts/activities/activity-sub-groups/{subgroup_uid}/approvals?cascade=false",
                        headers=headers,
                    )
                except Exception as e:
                    print(f"Failed to approve subgroup {subgroup_uid}: {e}")
                return subgroup_uid


async def match_synonym_to_activity(synonyms):
    headers = {"accept": "application/json, text/plain, */*"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.osb_base_url}/concepts/activities/activities?page_number=1&page_size=1000",
            headers=headers,
        )
        if response.status_code != 200:
            return None
    items = response.json().get("items", [])
    synonym_set = set(s.lower() for s in synonyms)
    for item in items:
        name = item.get("name", "").lower()
        if any(get_close_matches(name, synonym_set, n=1, cutoff=0.6)):
            return item
    return None


async def find_existing_activity_by_name(activity_name: str, library_name: str):
    """Helper function to find existing activity by name and check status"""
    endpoint = f"{settings.osb_base_url}/concepts/activities/activities"

    params = {
        "library_name": library_name,
        "page_size": 1000,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, params=params)
        if response.status_code == 200:
            data = response.json()
            # Find activity by name (case-insensitive)
            for item in data.get("items", []):
                if item.get("name", "").lower() == activity_name.lower():
                    return item
        return None


async def create_study_activities(
    study_uid: str,
    name: str,
    group_uid: str,
    subgroup_uid: str,
    soa_group_term_uid: str,
):
    response = None
    concept_already_exists = False

    try:
        response = await create_study_activities_concept(
            name=name,
            group_uid=group_uid,
            subgroup_uid=subgroup_uid,
            request_rationale="New activity",
            is_data_collected=False,
            flowchat_group={},
        )
    except Exception as e:
        error_message = str(e)
        if "409" in error_message:
            print(
                f"Activity concept already exists for '{name}', fetching existing activity..."
            )
            concept_already_exists = True
            existing_activity = await find_existing_activity_by_name(
                activity_name=name,
                library_name="Requested",
            )
            if existing_activity:
                response = existing_activity
                print(f"Found existing activity with UID: {response.get('uid')}")
            else:
                print(f"Error: Activity '{name}' already exists but could not be found")
                return None
        else:
            print(f"Error creating study activities concept: {e}")
            return None

    if not response or not response.get("uid"):
        print("Error: No valid response or UID from concept creation")
        return None

    activity_uid = response.get("uid")
    approval_response = None

    if concept_already_exists:
        activity_status = response.get("status", "").lower()
        if activity_status == "final":
            print(f"Activity '{name}' is already approved (status: Final)")
            approval_response = response
        else:
            try:
                approval_response = await create_study_activities_approvals(
                    activity_uid=activity_uid
                )
                print(f"Created approvals for existing activity '{name}'")
            except Exception as e:
                error_message = str(e)
                if "400" in error_message or "422" in error_message:
                    print(
                        f"Approvals may already exist for '{name}', checking status..."
                    )
                    if activity_status in ["final", "approved"]:
                        approval_response = response
                    else:
                        print(
                            f"Error: Activity '{name}' exists but is not approved and approvals creation failed: {e}"
                        )
                        return None
                else:
                    print(f"Error creating study activities approvals: {e}")
                    return None
    else:
        try:
            approval_response = await create_study_activities_approvals(
                activity_uid=activity_uid
            )
        except Exception as e:
            print(f"Error creating study activities approvals: {e}")
            return None

    if not approval_response or not approval_response.get("uid"):
        print("Error: No valid approval response or UID")
        return None

    try:
        batch_response = await create_study_activities_batch(
            study_uid=study_uid,
            activity_uid=approval_response.get("uid"),
            activity_group_uid=approval_response.get("activity_groupings", [{}])[0].get(
                "activity_group_uid", ""
            ),
            activity_subgroup_uid=approval_response.get("activity_groupings", [{}])[
                0
            ].get("activity_subgroup_uid", ""),
            soa_group_term_uid=soa_group_term_uid,
        )
    except Exception as e:
        print(f"Error creating study activities batch: {e}")
        return None
    return batch_response


async def create_study_activity(version: list, study_uid: str, study_number: str):
    design = version.get("studyDesigns", [])

    for des in design:
        activities = des.get("activities", [])
        biomedical_concepts = version.get("biomedicalConcepts", [])

        for act in activities:
            label = act.get("label", "")  # noqa: F841
            description = act.get("description", "")
            name = act.get("name", "")
            bc_ids = act.get("biomedicalConceptIds")

            if "grouping activity" in (description or "").lower():
                for child_id in act.get("childIds", []):
                    child_act = next(
                        (a for a in activities if a.get("id") == child_id), None
                    )
                    if not child_act:
                        continue
                    child_label = (
                        child_act.get("label", "")
                        or child_act.get("name", "")
                        or child_act.get("description", "")
                    )
                    child_bc_ids = child_act.get("biomedicalConceptIds")
                    if not child_bc_ids:
                        matched_act = await search_frontend_activity(name=child_label)
                        if matched_act:
                            grouping = matched_act.get("activity_groupings", [])[0]
                            await create_study_activities(
                                study_uid=study_uid,
                                name=name,
                                group_uid=str(grouping.get("activity_grouping_uid")),
                                subgroup_uid=str(
                                    grouping.get("activity_subgrouping_uid")
                                ),
                                soa_group_term_uid="CTTerm_000067",  # Todo: hardcoded soa group term uid
                            )
                        else:
                            group_id = await get_or_create_group(group_name=description)
                            subgroup_id = await get_or_create_subgroup(
                                subgroup_name=description, group_uid=group_id
                            )
                            await create_study_activities(
                                study_uid=study_uid,
                                name=name,
                                group_uid=str(group_id),
                                subgroup_uid=str(subgroup_id),
                                soa_group_term_uid="CTTerm_000067",  # Todo: hardcoded soa group term uid
                            )

                    else:
                        for bc_id in bc_ids:
                            bc = next(
                                (
                                    b
                                    for b in biomedical_concepts
                                    if b.get("id") == bc_id
                                ),
                                None,
                            )
                            if bc:
                                match = await match_synonym_to_activity(
                                    bc.get("synonyms", [])
                                )
                                if match:
                                    grouping = match.get("activity_groupings", [])[0]
                                    await create_study_activities(
                                        study_uid=study_uid,
                                        name=name,
                                        group_uid=str(
                                            grouping.get("activity_grouping_uid")
                                        ),
                                        subgroup_uid=str(
                                            grouping.get("activity_subgrouping_uid")
                                        ),
                                        soa_group_term_uid="CTTerm_000067",  # Todo: hardcoded soa group term uid
                                    )
            else:
                if not bc_ids:
                    matched_act = await search_frontend_activity(name=name)
                    if matched_act:
                        grouping = matched_act.get("activity_groupings", [])[0]
                        try:
                            await create_study_activities(
                                study_uid=study_uid,
                                name=name,
                                group_uid=str(grouping.get("activity_group_uid")),
                                subgroup_uid=str(grouping.get("activity_subgroup_uid")),
                                soa_group_term_uid="CTTerm_000067",  # Todo: hardcoded soa group term uid
                            )
                        except Exception as e:
                            print(f"Failed to create study activity: {e}")

                    else:
                        tbd_name = f"TBD_{study_number}"  # Todo: hardcoded tbd name
                        group_id = await get_or_create_group(tbd_name)
                        subgroup_id = await get_or_create_subgroup(
                            subgroup_name=tbd_name, group_uid=group_id
                        )
                        await create_study_activities(
                            study_uid=study_uid,
                            name=name,
                            group_uid=str(group_id),
                            subgroup_uid=str(subgroup_id),
                            soa_group_term_uid="CTTerm_000067",  # Todo: hardcoded soa group term uid
                        )
                else:
                    for bc_id in bc_ids:
                        bc = next(
                            (b for b in biomedical_concepts if b.get("id") == bc_id),
                            None,
                        )
                        if bc:
                            match = await match_synonym_to_activity(
                                bc.get("synonyms", [])
                            )
                            if match:
                                grouping = match.get("activity_groupings", [])[0]
                                await create_study_activities(
                                    study_uid=study_uid,
                                    name=name,
                                    group_uid=str(grouping.get("activity_group_uid")),
                                    subgroup_uid=str(
                                        grouping.get("activity_subgroup_uid")
                                    ),
                                    soa_group_term_uid="CTTerm_000067",  # Todo: hardcoded soa group term uid
                                )
    print("Study activities created successfully.")
