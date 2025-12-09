import httpx

from ..settings import settings
from .osb_api import create_high_level_design


async def create_study_high_level_design(study_designs: list, study_uid: str):
    headers = {"accept": "application/json, text/plain, */*"}
    study_type_code = {}
    trial_phase_code = {}
    trial_type_codes = []
    if study_designs:
        design = study_designs[0]
        studyType = design.get("studyType", {})
        study_type_code = studyType.get("code", "")

        if study_type_code:
            endpoint = f"{settings.osb_base_url}/ct/terms?codelist_uid=C99077&page_number=1&page_size=1000"
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        codelists = item.get("attributes", {}).get("concept_id", "")
                        if codelists == study_type_code:
                            study_type_code = {
                                "term_uid": item.get("term_uid", "string"),
                                "name": item.get("name", {}).get(
                                    "sponsor_preferred_name", "string"
                                ),
                            }
                            break

        studyPhase = design.get("studyPhase", {})
        standardCode = studyPhase.get("standardCode", {})
        phase_code = standardCode.get("code", "")

        if phase_code:
            endpoint = f"{settings.osb_base_url}/ct/terms?codelist_uid=C66737&page_number=1&page_size=1000"
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        codelists = item.get("attributes", {}).get("concept_id", "")
                        if codelists == phase_code:
                            trial_phase_code = {
                                "term_uid": item.get("term_uid", "string"),
                                "name": item.get("name", {}).get(
                                    "sponsor_preferred_name", "string"
                                ),
                            }
                            break

        subTypes = design.get("subTypes", {})
        trial_type_codes_list = [
            subtype.get("code", "") for subtype in subTypes if "code" in subtype
        ]

        if trial_type_codes_list:
            endpoint = f"{settings.osb_base_url}/ct/terms?codelist_uid=C66739&page_number=1&page_size=1000"
            headers = {"accept": "application/json, text/plain, */*"}
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for code in trial_type_codes_list:
                        for item in items:
                            codelists = item.get("attributes", {}).get("concept_id", "")
                            if codelists == code:
                                trial_type_codes.append({
                                    "term_uid": item.get("term_uid", "string"),
                                    "name": item.get("name", {}).get(
                                        "sponsor_preferred_name", "string"
                                    ),
                                })
                                break

    response = await create_high_level_design(
        study_uid=study_uid,
        study_type_code=study_type_code,
        phase_type_code=trial_phase_code,
        trial_type_codes=trial_type_codes,
    )
    print("Study high level design created successfully.")

    return response
