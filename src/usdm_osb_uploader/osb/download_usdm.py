import json

import httpx

from ..settings import settings


async def download_usdm(study_uid: str):
    file_path = f"./{study_uid}_usdm.json"
    endpoint = f"{settings.osb_base_url}/usdm/v3/studyDefinitions/{study_uid}"
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        response.raise_for_status()
        with open(file_path, "w") as f:
            json.dump(response.json(), f, indent=2)
    print(f"USDM file downloaded successfully for study UID: {study_uid}")
