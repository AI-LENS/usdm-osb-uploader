from typing import Annotated

import httpx
from pydantic import BaseModel, Field, RootModel

from ..settings import settings


class StudyMinimal(BaseModel):
    uid: Annotated[
        str, Field(description="UID of the study, e.g. 'Study_000001'", title="Uid")
    ]
    id: Annotated[
        str | None,
        Field(description="ID of the study, e.g. 'NN1234-56789'", title="Id"),
    ] = None
    acronym: Annotated[str | None, Field(title="Acronym")] = None


async def create_study(name: str, description: str):
    latest_study_number_url = rf"{settings.osb_base_url}/studies/list?minimal=true"

    headers = {"accept": "application/json, text/plain, */*"}
    async with httpx.AsyncClient() as client:
        response = await client.get(latest_study_number_url, headers=headers)
        response.raise_for_status()
        data = RootModel[list[StudyMinimal]].model_validate(response.json())
        max_study_number = max(
            int(item.id[4:])
            for item in data.root
            if item.id is not None and item.id.startswith("999-")
        )
        current_study_number = str(max_study_number + 1)
        print(current_study_number)

        study_payload = {
            "study_acronym": name[:20],  # Truncate to 20 chars if needed
            "study_subpart_acronym": None,  # Can be customized or left empty
            "description": description,
            "study_parent": None,
            "study_parent_part_uid": ["999"],
            "study_description": {"study_title": name},
            "project_number": "999",
            "study_number": current_study_number,
            # "study_number":study_info.get("name","")[-4:]# Assuming this is a new study with no parent
        }
        new_study_endpoint = f"{settings.osb_base_url}/studies"
        response = await client.post(
            new_study_endpoint, json=study_payload, headers=headers
        )
    if (
        response.status_code == 422
        or response.status_code == 400
        or response.status_code == 404
        or response.status_code == 409
        or response.status_code == 500
    ):
        raise Exception(
            f"Failed to create study: {response.status_code} - {response.text}"
        )
    res = response.json()
    return res, current_study_number


async def create_high_level_design(
    study_uid: str,
    study_type_code: dict | None,
    phase_type_code: dict | None,
    trial_type_codes: list[dict] | None,
):
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}"
    req_body = {
        "current_metadata": {
            "high_level_study_design": {
                "study_type_code": study_type_code,
                "study_type_null_value_code": None,
                "trial_type_codes": trial_type_codes,
                "trial_type_null_value_code": None,
                "trial_phase_code": phase_type_code,
                "trial_phase_null_value_code": None,
                "is_extension_trial": None,
                "is_extension_trial_null_value_code": None,
                "is_adaptive_design": None,
                "is_adaptive_design_null_value_code": None,
                "study_stop_rules": "NONE",
                "study_stop_rules_null_value_code": None,
                "confirmed_response_minimum_duration": None,
                "confirmed_response_minimum_duration_null_value_code": None,
                "post_auth_indicator": None,
                "post_auth_indicator_null_value_code": None,
                "trial_intent_types_codes": None,
            }
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.patch(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study properties: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_structure_study_arm(
    study_uid: str,
    arm_type_uid: str,
    name: str,
    short_name: str,
    randomization_group: str,
    code: str,
    description: str,
):  # working fine
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-arms"
    req_body = {
        "arm_type_uid": arm_type_uid,
        "name": name,
        "short_name": short_name,
        "randomization_group": randomization_group,
        "code": code,
        "arm_colour": "#BDBDBD",  # Default color, can be customized
        "description": description,
        "number_of_subjects": 0,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study arm: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_structure_study_epoch(
    study_uid: str,
    epoch_type: str,
    epoch_subtype: str,
    start_rule: str,
    end_rule: str,
    order: str,
    description: str,
):
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-epochs"
    req_body = {
        "epoch_type": epoch_type,
        "epoch": epoch_subtype,
        "epoch_subtype": epoch_subtype,
        "start_rule": start_rule,
        "end_rule": end_rule,
        "study_uid": study_uid,
        "order": order,
        "description": description,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study epoch: {response.status_code} - {response.text}"
            )
        return response.json()


async def create_study_structure_study_element(
    study_uid: str,
    name: str,
    code: str,
    start_rule: str,
    end_rule: str,
    subtype_uid: str,
    short_name: str,
    description: str,
):  # working fine
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-elements"
    req_body = {
        "name": name,
        "short_name": short_name,
        "code": code,
        "description": description,
        "planned_duration": None,
        "start_rule": start_rule,
        "end_rule": end_rule,
        "element_colour": "#BDBDBD",  # Default color, can be customized
        "element_subtype_uid": subtype_uid,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study element: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_structure_study_element_patch(
    study_uid: str, name: str, subtype_uid: str, short_name: str, study_element_uid: str
):  # working fine
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-elements/{study_element_uid}"
    req_body = {
        "name": name,
        "short_name": short_name,
        "element_subtype_uid": subtype_uid,
    }
    async with httpx.AsyncClient() as client:
        response = await client.patch(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to update study element: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_population_api(
    study_uid: str,
    therapeutic_area_codes: list[dict],
    disease_condition_or_indication_codes: list[dict],
    sex_of_participants_code: dict,
    rare_disease_indicator: bool,
    healthy_subject_indicator: bool,
    planned_minimum_age_of_subjects: dict,
    planned_maximum_age_of_subjects: dict,
    stable_disease_minimum_duration: dict,
    pediatric_study_indicator: bool,
    pediatric_postmarket_study_indicator: bool,
    pediatric_investigation_plan_indicator: bool,
    relapse_criteria: str,
    relapse_criteria_null_value_code: dict,
    number_of_expected_subjects: str,
):
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}"
    req_body = {
        "current_metadata": {
            "study_population": {
                "therapeutic_area_codes": therapeutic_area_codes,
                "therapeutic_area_null_value_code": None,
                "disease_condition_or_indication_codes": disease_condition_or_indication_codes,
                "disease_condition_or_indication_null_value_code": None,
                "diagnosis_group_null_value_code": None,
                "sex_of_participants_code": sex_of_participants_code,
                "sex_of_participants_null_value_code": None,
                "rare_disease_indicator": rare_disease_indicator,
                "rare_disease_indicator_null_value_code": None,
                "healthy_subject_indicator": healthy_subject_indicator,
                "healthy_subject_indicator_null_value_code": None,
                "planned_minimum_age_of_subjects": planned_minimum_age_of_subjects,
                "planned_minimum_age_of_subjects_null_value_code": None,
                "planned_maximum_age_of_subjects": planned_maximum_age_of_subjects,
                "planned_maximum_age_of_subjects_null_value_code": None,
                "stable_disease_minimum_duration": stable_disease_minimum_duration,
                "stable_disease_minimum_duration_null_value_code": None,
                "pediatric_study_indicator": pediatric_study_indicator,
                "pediatric_study_indicator_null_value_code": None,
                "pediatric_postmarket_study_indicator": pediatric_postmarket_study_indicator,
                "pediatric_postmarket_study_indicator_null_value_code": None,
                "pediatric_investigation_plan_indicator": pediatric_investigation_plan_indicator,
                "pediatric_investigation_plan_indicator_null_value_code": None,
                "relapse_criteria": relapse_criteria,
                "relapse_criteria_null_value_code": relapse_criteria_null_value_code,
                "number_of_expected_subjects": number_of_expected_subjects,
                "number_of_expected_subjects_null_value_code": None,
            }
        },
        "study_parent_part_uid": None,
    }
    async with httpx.AsyncClient() as client:
        response = await client.patch(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            print(f"Error response: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json()


async def create_study_criteria_inclusion_criteria_templates(
    study_uid: str, name: str, library_name: str, type_uid: str
):  # criteria_preinstance
    endpoint = f"{settings.osb_base_url}/criteria-templates"
    req_body = {
        "name": name,
        "library_name": library_name,
        "type_uid": type_uid,
        "study_uid": study_uid,
        "guidance_text": None,
        "indication_uids": None,
        "category_uids": None,
        "sub_category_uids": None,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study criteria-template - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_criteria_inclusion_approvals(
    criteria_template_uid: str,
):  # criteria_template
    endpoint = f"{settings.osb_base_url}/criteria-templates/{criteria_template_uid}/approvals?cascade=true"
    HEADERS = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, headers=HEADERS)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study criteria-approval - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_concepts_numeric(
    value: str, library_name: str, template_parameter: bool
):  # numeric_value
    endpoint = f"{settings.osb_base_url}/concepts/numeric-values"
    req_body = {
        "value": value,
        "library_name": library_name,
        "template_parameter": template_parameter,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study concept-numeric - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_concepts_numeric_with_unit(
    name: str,
    name_sentence_case: str,
    definition: str,
    abbreviation: str,
    library_name: str,
    template_parameter: bool,
    value: int,
    unit_definition_uid: str,
):  # numeric_value_with_unit
    endpoint = f"{settings.osb_base_url}/concepts/numeric-values-with-unit"
    req_body = {
        "name": name,
        "name_sentence_case": name_sentence_case,
        "definition": definition,
        "abbreviation": abbreviation,
        "library_name": library_name,
        "template_parameter": template_parameter,
        "value": value,
        "unit_definition_uid": unit_definition_uid,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study concept-numeric-with-unit - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_criteria_inclusion_create_criteria(
    study_uid: str, uid: str, parameter_terms: list[dict]
):  # study_criteria
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-criteria?create_criteria=true"
    req_body = {
        "criteria_data": {
            "criteria_template_uid": uid,
            "parameter_terms": parameter_terms,
            "library_name": "Sponsor",
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study criteria - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_purpose_objective_templates(
    study_uid: str, name: str, library_name: str
):
    endpoint = f"{settings.osb_base_url}/objective-templates"
    req_body = {
        "name": name,
        "library_name": library_name,
        "study_uid": study_uid,
        "guidance_text": None,
        "indication_uids": None,
        "category_uids": None,
        "is_confirmatory_testing": False,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create objective template - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def get_objective_template_status(objective_template_uid: str) -> dict:
    """Get the current status of an objective template"""
    endpoint = f"{settings.osb_base_url}/objective-templates/{objective_template_uid}"
    headers = {"accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, headers=headers)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(f"Objective template {objective_template_uid} not found")
        response.raise_for_status()
        return response.json()


async def create_study_objective_approvals(objective_template_uid: str):
    # First check if the objective template is already approved
    try:
        template_data = await get_objective_template_status(objective_template_uid)

        # Check if the template is already in "Final" status (approved)
        if template_data.get("status") == "Final":
            print(
                f"Objective template {objective_template_uid} is already approved (status: Final)"
            )
            return template_data

        # If not approved, proceed with approval
        endpoint = f"{settings.osb_base_url}/objective-templates/{objective_template_uid}/approvals?cascade=true"
        HEADERS = {"Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, headers=HEADERS)
            if (
                response.status_code == 422
                or response.status_code == 400
                or response.status_code == 404
                or response.status_code == 409
                or response.status_code == 500
            ):
                raise Exception(
                    f"Failed to approve objective template - Invalid data: {response.status_code} - {response.text}"
                )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        if "already approved" in str(e):
            raise e
        raise Exception(f"Failed to check or approve objective template: {e}")


async def create_study_objective_create_objective(
    study_uid: str, uid: str, objective_level_uid: str
):
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-objectives?create_objective=true"
    req_body = {
        "objective_level_uid": objective_level_uid,
        "objective_data": {
            "parameter_terms": [],
            "objective_template_uid": uid,
            "library_name": "User Defined",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study objective - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_purpose_endpoint_templates(
    study_uid: str, name: str, library_name: str
):
    endpoint = f"{settings.osb_base_url}/endpoint-templates"
    req_body = {
        "name": name,
        "library_name": library_name,
        "study_uid": study_uid,
        "guidance_text": None,
        "indication_uids": None,
        "category_uids": None,
        "is_confirmatory_testing": False,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create endpoint template - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def get_endpoint_template_status(endpoint_template_uid: str) -> dict:
    """Get the current status of an endpoint template"""
    endpoint = f"{settings.osb_base_url}/endpoint-templates/{endpoint_template_uid}"
    headers = {"accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, headers=headers)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(f"Endpoint template {endpoint_template_uid} not found")
        response.raise_for_status()
        return response.json()


async def create_study_endpoint_approvals(endpoint_template_uid: str):
    # First check if the endpoint template is already approved
    try:
        template_data = await get_endpoint_template_status(endpoint_template_uid)

        # Check if the template is already in "Final" status (approved)
        if template_data.get("status") == "Final":
            print(
                f"Endpoint template {endpoint_template_uid} is already approved (status: Final)"
            )
            return template_data

        # If not approved, proceed with approval
        endpoint = f"{settings.osb_base_url}/endpoint-templates/{endpoint_template_uid}/approvals?cascade=true"
        HEADERS = {"Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, headers=HEADERS)
            if (
                response.status_code == 422
                or response.status_code == 400
                or response.status_code == 404
                or response.status_code == 409
                or response.status_code == 500
            ):
                raise Exception(
                    f"Failed to approve endpoint template - Invalid data: {response.status_code} - {response.text}"
                )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        if "already approved" in str(e):
            raise e
        raise Exception(f"Failed to check or approve endpoint template: {e}")


async def create_study_endpoint_create_objective(
    study_uid: str,
    uid: str,
    study_objective_uid: str,
    endpoint_level_uid: str,
    endpoint_sublevel_uid: str,
):
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-endpoints?create_endpoint=true"
    req_body = {
        "study_objective_uid": study_objective_uid,
        "endpoint_level_uid": endpoint_level_uid,
        "endpoint_sublevel_uid": endpoint_sublevel_uid,
        "endpoint_data": {
            "parameter_terms": [],
            "endpoint_template_uid": uid,
            "library_name": "User Defined",
        },
        "endpoint_units": None,
        "timeframe_uid": None,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study endpoint - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_structure_study_visit(
    study_uid: str,
    is_global_anchor_visit: bool,
    study_epoch_uid: str,
    visit_type_uid: str,
    visit_contact_mode_uid: str,
    time_value: str,
    time_unit_uid: str,
    description: str,
    min_visit_window_value: str = "0",
    max_visit_window_value: str = "0",
    visit_window_unit_uid: str = "UnitDefinition_000364",
):
    # get global anchor visit ct
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            settings.osb_base_url
            + "/ct/terms?codelist_name=Time+Point+Reference&filters={%22attributes.name_submission_value%22:{%22v%22:[%22GLOBAL%20ANCHOR%20VISIT%20REFERENCE%22],%22op%22:%22eq%22}}"
        )
        resp.raise_for_status()
        data = resp.json()
        time_reference_uid = data["items"][0]["term_uid"]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            settings.osb_base_url
            + "/ct/terms?codelist_name=Epoch+Allocation&filters={%22attributes.name_submission_value%22:{%22v%22:[%22PREVIOUS%20VISIT%22],%22op%22:%22eq%22}}"
        )
        resp.raise_for_status()
        data = resp.json()
        epoch_allocation_uid = data["items"][0]["term_uid"]

    preview_endpoint = (
        f"{settings.osb_base_url}/studies/{study_uid}/study-visits/preview"
    )
    req_body = {
        "is_global_anchor_visit": False,
        "visit_class": "SINGLE_VISIT",
        "show_visit": True,
        "min_visit_window_value": min_visit_window_value,
        "max_visit_window_value": max_visit_window_value,
        "visit_subclass": "SINGLE_VISIT",
        "visit_window_unit_uid": visit_window_unit_uid,
        "study_epoch_uid": study_epoch_uid,
        "epoch_allocation_uid": epoch_allocation_uid,
        "visit_type_uid": visit_type_uid,
        "visit_contact_mode_uid": visit_contact_mode_uid,
        "time_reference_uid": time_reference_uid,
        "time_value": time_value,
        "time_unit_uid": time_unit_uid,
        "description": description,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(preview_endpoint, json=req_body)
        response.raise_for_status()
        preview = response.json()

    submit_endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-visits"

    submit_req_body = req_body.copy()
    submit_req_body["study_day_label"] = preview["study_day_label"]
    submit_req_body["study_week_label"] = preview["study_week_label"]
    if is_global_anchor_visit:
        submit_req_body["is_global_anchor_visit"] = is_global_anchor_visit

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(submit_endpoint, json=submit_req_body)
        response.raise_for_status()
        return response.json()


async def create_study_activities_concept(
    name: str,
    group_uid: str,
    subgroup_uid: str,
    request_rationale: str,
    is_data_collected: bool,
    flowchat_group: dict,
):
    endpoint = f"{settings.osb_base_url}/concepts/activities/activities"
    HEADERS = {"Content-Type": "application/json"}
    req_body = {
        "name": name,
        "name_sentence_case": name.lower(),
        "library_name": "Requested",
        "activity_groupings": [
            {"activity_group_uid": group_uid, "activity_subgroup_uid": subgroup_uid}
        ],
        "request_rationale": request_rationale,
        "is_request_final": False,
        "is_data_collected": is_data_collected,
        "flowchat_group": flowchat_group,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=req_body, headers=HEADERS)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study activity-concept - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_activities_approvals(activity_uid: str):
    endpoint = f"{settings.osb_base_url}/concepts/activities/activities/{activity_uid}/approvals"
    HEADERS = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, headers=HEADERS)
        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create study activity-approval - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()


async def create_study_activity_api(
    study_uid: str,
    group_uid: str,
    subgroup_uid: str,
    activity_uid: str,
    posted_uids: set,
):
    if activity_uid in posted_uids:
        return
    post_payload = {
        "soa_group_term_uid": "CTTerm_000067",
        "activity_uid": activity_uid,
        "activity_subgroup_uid": subgroup_uid,
        "activity_group_uid": group_uid,
        "activity_instance_uid": None,
    }
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-activities"
    HEADERS = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=post_payload, headers=HEADERS)
        if response.status_code == 409:
            # Log and continue if the activity already exists
            print(f"Activity already exists: {response.text}")
            return
        if response.status_code in {422, 400, 404, 500}:
            raise Exception(
                f"Failed to create activity: {response.status_code} - {response.text}"
            )

    return response.json()


async def create_study_activity_schedule(
    study_uid: str, study_activity_uid: str, study_visit_uid: str
):
    """
    Create a study activity schedule linking an activity to a visit.

    Args:
        study_uid: The study UID
        study_activity_uid: The study activity UID
        study_visit_uid: The study visit UID
    """
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-activity-schedules"
    headers = {"Content-Type": "application/json"}

    payload = {
        "study_activity_uid": study_activity_uid,
        "study_visit_uid": study_visit_uid,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, headers=headers)

        if (
            response.status_code == 422
            or response.status_code == 400
            or response.status_code == 404
            or response.status_code == 409
            or response.status_code == 500
        ):
            raise Exception(
                f"Failed to create activity schedule: {response.status_code} - {response.text}"
            )

        response.raise_for_status()
        return response.json()


async def create_study_activities_batch(
    study_uid: str,
    activity_uid: str,
    activity_group_uid: str,
    activity_subgroup_uid: str,
    soa_group_term_uid: str,
):  # study_objective
    endpoint = f"{settings.osb_base_url}/studies/{study_uid}/study-activities/batch"
    req_body = [
        {
            "method": "POST",
            "content": {
                "soa_group_term_uid": soa_group_term_uid,
                "activity_uid": activity_uid,
                "order": None,
                "activity_group_uid": activity_group_uid,
                "activity_subgroup_uid": activity_subgroup_uid,
            },
        }
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(endpoint, json=req_body)
        if response.status_code == 422 or response.status_code == 404:
            raise Exception(
                f"Failed to create study objective - Invalid data: {response.status_code} - {response.text}"
            )
        response.raise_for_status()
        return response.json()
