import re

from .osb_api import (
    create_study_criteria_inclusion_approvals,
    create_study_criteria_inclusion_create_criteria,
    create_study_criteria_inclusion_criteria_templates,
)


async def create_study_criteria(study_version: list, study_uid: str):
    study_designs = study_version.get("studyDesigns", [])
    criteria_texts = study_version.get("eligibilityCriterionItems", [])
    text_map = {c["id"]: c["text"] for c in criteria_texts}

    mapped_criteria = []
    for design in study_designs:
        for crit in design.get("eligibilityCriteria", []):
            cat = crit.get("category", {}).get("decode", "").lower()
            crit_type = "inclusion" if cat.startswith("in") else "exclusion"
            item_id = crit.get("criterionItemId")
            raw_text = text_map.get(item_id, "")
            mapped_criteria.append({"id": item_id, "type": crit_type, "text": raw_text})

    for crit in mapped_criteria:
        is_inclusion = crit["type"] == "inclusion"
        type_uid = "CTTerm_000028" if is_inclusion else "CTTerm_000029"

        raw_html = crit.get("text", "")
        plain_text = re.sub(r"<[^>]+>", "", raw_html).strip()

        template_response = await create_study_criteria_inclusion_criteria_templates(
            study_uid=study_uid,
            name=plain_text.replace("[", "(").replace("]", ")"),
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
