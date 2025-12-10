import re

import httpx

from ..settings import settings
from .osb_api import (
    create_study_criteria_inclusion_approvals,
    create_study_criteria_inclusion_create_criteria,
    create_study_criteria_inclusion_criteria_templates,
)


async def create_study_criteria(study_version: dict, study_uid: str):
    study_designs = study_version.get("studyDesigns", [])
    criteria_texts = study_version.get("eligibilityCriterionItems", [])
    text_map = {c["id"]: c["text"] for c in criteria_texts}

    mapped_criteria = []
    for design in study_designs:
        for crit in design.get("eligibilityCriteria", []):
            crit_type = crit.get("category", {}).get("decode", "").lower()
            item_id = crit.get("criterionItemId")
            raw_text = text_map.get(item_id, "")
            mapped_criteria.append({"id": item_id, "type": crit_type, "text": raw_text})

    for crit in mapped_criteria:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.osb_base_url}/ct/terms?codelist_uid=C66797&page_number=1&page_size=1000"  # TODO: hardcoded code
            )
            for item in response.json().get("items", []):
                if (
                    item.get("name", {}).get("sponsor_preferred_name", "").lower()
                    == crit["type"]
                ):
                    type_uid = item.get("term_uid")
                    break

        raw_html = crit.get("text", "")
        plain_text = re.sub(r"<[^>]+>", "", raw_html).strip()

        template_response = await create_study_criteria_inclusion_criteria_templates(
            study_uid=study_uid,
            name=plain_text.replace("[", "(").replace("]", ")")[:200],
            library_name="User Defined",
            type_uid=type_uid,
        )

        if template_response.get("uid") is None:
            continue

        # Try to approve the template, but handle the case where it's already approved
        try:
            approval_response = await create_study_criteria_inclusion_approvals(
                template_response.get("uid")
            )
            template_uid = approval_response.get("uid")
        except Exception as e:
            if "isn't in draft status" in str(e):
                # Template is already approved, use the original template UID
                print(
                    f"Template {template_response.get('uid')} is already approved, proceeding with creation"
                )
                template_uid = template_response.get("uid")
            else:
                # Re-raise other exceptions
                raise e

        create_response = await create_study_criteria_inclusion_create_criteria(  # noqa: F841
            study_uid=study_uid, uid=template_uid, parameter_terms=[]
        )
    print("Study criteria created successfully.")
