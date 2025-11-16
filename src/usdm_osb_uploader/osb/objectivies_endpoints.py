import httpx

from ..settings import settings
from .osb_api import (
    create_study_endpoint_approvals,
    create_study_endpoint_create_objective,
    create_study_objective_approvals,
    create_study_objective_create_objective,
    create_study_purpose_endpoint_templates,
    create_study_purpose_objective_templates,
)


async def create_study_objective_endpoint(study_design: dict, study_uid: str):
    headers = {"accept": "application/json, text/plain, */*"}
    design = study_design[0]
    objectives = design.get("objectives", [])

    for obj in objectives:
        template_response = await create_study_purpose_objective_templates(
            study_uid=study_uid,
            name=obj.get("text", "").replace("[", "(").replace("]", ")"),
            library_name="User Defined",
        )

        template_uid = template_response.get("uid")

        approval_response = await create_study_objective_approvals(template_uid)  # noqa: F841
        # print(approval_response.get("uid"))

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.osb_base_url}/ct/terms?codelist_uid=CTCodelist_000003&page_number=1&page_size=1000"
            )
            for item in response.json().get("items", []):
                if (
                    item.get("name", {}).get("sponsor_preferred_name", "").lower()
                    == obj.get("level", {}).get("decode", "").lower()
                ):
                    level_uid = item.get("term_uid")
                    break

        create_response = await create_study_objective_create_objective(  # noqa: F841
            study_uid=study_uid, uid=template_uid, objective_level_uid=None
        )

        endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-objectives"
        study_objective_uid = None  # Initialize the variable
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers)
            # print(response.json().get("items", []))
            for existing in response.json().get("items", []):
                if existing.get("objective", {}).get("name", "") == obj.get("text", ""):
                    study_objective_uid = existing.get("study_objective_uid")
                    print(study_objective_uid)
                    break

        # Check if we found the study objective
        if study_objective_uid is None:
            print(
                f"Warning: Could not find study objective UID for objective: {obj.get('text', '')}"
            )
            continue  # Skip creating endpoints for this objective

        for obj_end in obj.get("endpoints", []):
            endpoint_template_response = await create_study_purpose_endpoint_templates(
                study_uid=study_uid,
                name=obj_end.get("text", "").replace("[", "(").replace("]", ")"),
                library_name="User Defined",
            )

            endpoint_template_uid = endpoint_template_response.get("uid")

            approval_response = await create_study_endpoint_approvals(  # noqa: F841
                endpoint_template_uid
            )  # noqa: F841

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.osb_base_url}/ct/terms?codelist_uid=CTCodelist_000004&page_number=1&page_size=1000"
                )
                endpoint_level_uid = None
                for item in response.json().get("items", []):
                    if (
                        item.get("name", {}).get("sponsor_preferred_name", "").lower()
                        == obj_end.get("level", {}).get("decode", "").lower()
                    ):
                        endpoint_level_uid = item.get("term_uid")
                        break

            create_response = await create_study_endpoint_create_objective(  # noqa: F841
                study_uid=study_uid,
                uid=endpoint_template_uid,
                study_objective_uid=study_objective_uid,
                endpoint_level_uid=endpoint_level_uid,
                endpoint_sublevel_uid=None,
            )
    print("Study objectives and endpoints created successfully.")
