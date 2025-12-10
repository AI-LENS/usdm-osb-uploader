import httpx

from ..settings import settings
from .osb_api import create_study_structure_study_element


async def create_study_element(study_designs: list, study_uid: str):
    design = study_designs[0]
    elements = design.get("elements", [])
    for elem in elements:
        name = elem.get("name", "")
        label = name.lower() if len(name) > 3 else elem.get("label", "").lower()
        start_rule = elem.get("transitionStartRule", {}).get("text", "")
        end_rule = (
            elem.get("transitionEndRule", {}).get("text", None)
            if elem.get("transitionEndRule")
            else None
        )
        description = elem.get("description", "")

        if label in [
            "screening",
            "check in",
            "check-in",
            "run-in",
            "run in",
            "follow-up",
            "follow up",
            "wash out",
            "wash-out",
        ]:
            code = "CTTerm_000143"  # TODO: hardcoded code
        else:
            code = "CTTerm_000144"  # TODO: hardcoded code

        async with httpx.AsyncClient() as client:
            res = await client.get(
                (settings.osb_base_url)
                + '/ct/codelists?total_count=true&library_name=Sponsor&catalogue_name=SDTM+CT&filters={"attributes.submission_value":{"v":["ELEMSTP"],"op":"eq"}}'
            )
            data = res.json()
            subtype_uid = data.get("items", [])[0].get("codelist_uid")

            response = await client.get(
                f"{settings.osb_base_url}/ct/terms?codelist_uid={subtype_uid}&page_number=1&page_size=1000"
            )
            for item in response.json().get("items", []):
                if (
                    item.get("name", {})
                    .get("sponsor_preferred_name", "")
                    .lower()
                    .split("-")[0]
                    in label.lower()
                ):
                    subtype_uid = item.get("term_uid")
                    break
                else:
                    subtype_uid = "CTTerm_000147"  # TODO: hardcoded code

        element_name = name if len(name) > 3 else elem.get("label", "")

        print(f"Creating element: {element_name}, code: {code}, subtype: {subtype_uid}")

        element_response = await create_study_structure_study_element(  # noqa: F841
            study_uid=study_uid,
            name=element_name,
            code=code,
            start_rule=start_rule,
            end_rule=end_rule,
            subtype_uid=subtype_uid,
            short_name=element_name,
            description=description,
        )
    print("Study elements created successfully.")
