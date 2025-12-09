import json

import httpx

from ..settings import settings


async def download_usdm(study_id: str):
    headers = {"accept": "application/json, text/plain, */*"}
    study_uid = None
    endpoint = f"{settings.osb_base_url}/studies/list?minimal=true"
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint, headers=headers)
        if response.status_code == 200:
            study_data = response.json()
            for item in study_data:
                if item.get("id") == study_id:
                    study_uid = item.get("uid", "")
                    print(f"Study UID: {study_uid}")
                    break
            else:
                raise Exception(f"Study ID not found: {study_id}")
        else:
            raise Exception(
                f"Failed to get study data: {response.status_code} - {response.text}"
            )

    file_path = f"./{study_uid}_usdm.json"
    endpoint = f"{settings.osb_base_url}/usdm/v3/studyDefinitions/{study_uid}"
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        response.raise_for_status()
        with open(file_path, "w") as f:
            json.dump(response.json(), f, indent=2)
    print(f"USDM file downloaded successfully for study UID: {study_uid}")
