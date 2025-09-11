import httpx

from ..settings import settings
from .osb_api import create_study_structure_study_arm


async def create_study_arm(study_designs: list, study_uid: str):
    response = []
    design = study_designs[0]
    arms = design.get("arms", [])
    for arm in arms:
        keywords = ["placebo", "investigational", "comparator", "observational"]
        arm_type_decode = arm.get("type", {}).get("decode", "").lower()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.osb_base_url}/ct/terms?codelist_name=Arm%20Type&is_sponsor=false&page_number=1&page_size=100"
            )
        if response.status_code == 200:
            items = response.json().get("items", [])
            for keyword in keywords:
                if keyword in arm_type_decode:
                    for item in items:
                        sponsor_name = (
                            item.get("name", {})
                            .get("sponsor_preferred_name", "")
                            .lower()
                        )
                        if keyword in sponsor_name:
                            response = await create_study_structure_study_arm(
                                study_uid=study_uid,
                                arm_type_uid=item.get("term_uid", "UNKNOWN_UID"),
                                name=arm.get("name", ""),
                                short_name=arm.get("name", ""),
                                randomization_group=arm.get("id", ""),
                                code=arm.get("name", ""),
                                description=arm.get("description", ""),
                            )
    print("Study arms created successfully.")
