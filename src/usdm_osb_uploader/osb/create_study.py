from .osb_api import create_study


async def create_study_id(usdm_data: dict) -> dict:
    study_info = usdm_data.get("study", {})

    study_versions = study_info.get("versions", [])
    study_titles = study_versions[0].get("titles", [])

    for title in study_titles:
        if title.get("type", {}).get("decode", "") == "Official Study Title":
            title1 = title.get("text", "")
        elif title.get("type", {}).get("decode", "") == "Brief Study Title":
            title2 = title.get("text", "")  # noqa: F841

    name = study_info.get("name", "")
    response, current_study_number = await create_study(name, title1)

    if response:
        study_uid = response["uid"]
        return study_uid, f"999-{current_study_number}"
    else:
        print("Failed to create study")
        return None
