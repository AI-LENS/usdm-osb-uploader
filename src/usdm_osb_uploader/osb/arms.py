import httpx

from ..settings import settings
from .osb_api import create_study_structure_study_arm


async def create_study_arm(study_designs: list, study_uid: str):
    response = []
    design = study_designs[0]
    arms = design.get("arms", [])
    arm_type_uid = None
    for arm in arms:
        keywords = ["placebo", "investigational", "comparator", "observational"]
        arm_type_decode = arm.get("type", {}).get("decode", "").lower()

        arm_type_decode = (
            "investigational" if "treatment" in arm_type_decode else arm_type_decode
        )  # todo: hardcoded investigational if arm type decode contains treatment

        async with httpx.AsyncClient() as client:
            res = await client.get(
                (settings.osb_base_url)
                + '/ct/codelists?total_count=true&library_name=Sponsor&catalogue_name=SDTM+CT&filters={"attributes.submission_value":{"v":["ARMTTP"],"op":"eq"}}'
            )
            data = res.json()
            arm_type_uid = data.get("items", [])[0].get("codelist_uid")
            response = await client.get(
                f"{settings.osb_base_url}/ct/terms?codelist_uid={arm_type_uid}&page_number=1&page_size=1000"
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
