import httpx
from pydantic import BaseModel

from ..settings import settings
from .osb_api import create_study_activity_schedule


class StudyActivity(BaseModel):
    """Study activity model from API response."""

    study_activity_uid: str
    activity_name: str
    activity_uid: str
    order: int


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


async def create_schedule_of_activity(study_designs: list, study_uid: str):
    design = study_designs[0]
    schedule = design.get("scheduleTimelines", [])[0]
    instances = schedule.get("instances", [])
    encounters = design.get("encounters", [])
    activities = await fetch_existing_study_activities(study_uid=study_uid)

    async with httpx.AsyncClient() as client:
        visits_response = await client.get(
            f"{settings.osb_base_url}/studies/{study_uid}/study-visits"
        )

    for instance in instances:
        enc_id = instance.get("encounterId")  # noqa: F841
        for enc in encounters:
            if enc.get("id") == enc_id:
                visit_description = enc.get("description", "")
                break
        for item in visits_response.json().get("items", []):
            if item.get("description", "") == visit_description:
                visit_id = item.get("uid", "")
                break
        # visit_id = "visit_mapping_encounter.get(enc_id)"
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
                error_message = str(e)
                if "400" in error_message or "422" in error_message:
                    print(
                        f"Activity schedule '{activity.activity_name}' -> '{visit_id}' may already exist, checking status..."
                    )
                else:
                    print(
                        f"Error creating activity schedule: '{activity.activity_name}' -> '{visit_id}'"
                    )

    print("Schedule of activities created successfully.")
