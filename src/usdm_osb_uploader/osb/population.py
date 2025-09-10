import httpx

from ..settings import settings
from .osb_api import create_study_population_api


async def create_study_population(study_designs: list, study_uid: str):
    design = study_designs[0]
    indications = design.get("indications", [])
    standard_codes = [
        indication.get("codes", [])
        for indication in indications
        if indication.get("codes")
    ]
    disease_conditions_or_indications_codes = []
    if standard_codes:
        # Validate disease condition codes with OSB API
        headers = {"accept": "application/json, text/plain, */*"}
        async with httpx.AsyncClient() as client:
            endpoint = f"{settings.osb_base_url}/dictionaries/terms?codelist_uid=DictionaryCodelist_000001&page_number=1&page_size=1000"
            response = await client.get(endpoint, headers=headers)
            if response.status_code == 200:
                valid_codes = response.json().get("items", [])
                valid_code_ids = [item.get("dictionary_id", "") for item in valid_codes]
                for codes_list in standard_codes:
                    for code_dict in codes_list:
                        code = code_dict.get("code", "")
                        if code in valid_code_ids:
                            # Find the matching term_uid from OSB
                            matching_item = next(
                                (
                                    item
                                    for item in valid_codes
                                    if item.get("dictionary_id", "") == code
                                ),
                                None,
                            )
                            if matching_item:
                                disease_conditions_or_indications_codes.append({
                                    "term_uid": matching_item.get("term_uid", "string"),
                                    "name": matching_item.get("name", ""),
                                })

    therapeutic_area = design.get("therapeuticAreas", [])
    therapeutic_area_codes = []
    if therapeutic_area:
        therapeutic_phase_codes = [
            area.get("decode", "") for area in therapeutic_area if "code" in area
        ]
        if therapeutic_phase_codes:
            headers = {"accept": "application/json, text/plain, */*"}
            async with httpx.AsyncClient() as client:
                endpoint = f"{settings.osb_base_url}/dictionaries/terms?codelist_uid=DictionaryCodelist_000001&page_number=1&page_size=1000"
                response = await client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    valid_decode = [item.get("name", "") for item in items]
                    for decode in therapeutic_phase_codes:
                        if decode in valid_decode:
                            matching_item = next(
                                (
                                    item
                                    for item in items
                                    if item.get("name", "") == decode
                                ),
                                None,
                            )
                            if matching_item:
                                therapeutic_area_codes.append({
                                    "term_uid": matching_item.get("term_uid", "string"),
                                    "name": matching_item.get("name", ""),
                                })
                                break

    population = design.get("population", {})
    number_of_expected_subjects = population.get(
        "plannedEnrollmentNumberQuantity", {}
    ).get("value")  # noqa: F841

    planned_sex = population.get("plannedSex", [])
    sex_of_participants_code = {}
    if planned_sex and planned_sex[0]:
        sex_of_participants_code = planned_sex[0].get("code", "")

        if sex_of_participants_code:
            endpoint = f"{settings.osb_base_url}/ct/terms?codelist_uid=C66732"
            headers = {"accept": "application/json, text/plain, */*"}
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, headers=headers)
            if response.status_code == 200:
                items = response.json().get("items", [])
                for item in items:
                    codelists = item.get("attributes", {}).get("concept_id", "")
                    if codelists == sex_of_participants_code:
                        sex_of_participants_code = {
                            "term_uid": item.get("term_uid", "string"),
                            "name": item.get("name", {}).get(
                                "sponsor_preferred_name", "string"
                            ),
                        }
                        break

    planned_age = population.get("plannedAge", {})
    planned_minimum_age_of_subjects = {}
    planned_maximum_age_of_subjects = {}
    if planned_age:
        planned_age_min = planned_age.get("minValue", {})
        planned_minimum_age_of_subjects = {
            "duration_value": planned_age_min.get("value"),
            "duration_unit_code": {"uid": "UnitDefinition_000368", "name": "years"},
        }

        planned_age_max = planned_age.get("maxValue", {})
        planned_maximum_age_of_subjects = {
            "duration_value": planned_age_max.get("value"),
            "duration_unit_code": {"uid": "UnitDefinition_000368", "name": "years"},
        }

    population_response = await create_study_population_api(  # noqa: F841
        study_uid=study_uid,
        therapeutic_area_codes=therapeutic_area_codes,
        disease_condition_or_indication_codes=disease_conditions_or_indications_codes,
        sex_of_participants_code=sex_of_participants_code,
        rare_disease_indicator=False,
        healthy_subject_indicator=False,
        planned_minimum_age_of_subjects=planned_minimum_age_of_subjects,
        planned_maximum_age_of_subjects=planned_maximum_age_of_subjects,
        stable_disease_minimum_duration={},
        pediatric_study_indicator=False,
        pediatric_postmarket_study_indicator=False,
        pediatric_investigation_plan_indicator=False,
        relapse_criteria="",
        relapse_criteria_null_value_code={"term_uid": ""},
        number_of_expected_subjects=number_of_expected_subjects,
    )
