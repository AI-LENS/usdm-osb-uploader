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

        if "screening" in label:
            code = "CTTerm_000143"
            subtype_uid = "CTTerm_000150"
        elif "check in" in label or "run-in" in label:
            code = "CTTerm_000143"
            subtype_uid = "CTTerm_000148"
        elif "follow up" in label or "follow-up" in label:
            code = "CTTerm_000143"
            subtype_uid = "CTTerm_000149"
        elif "wash out" in label or "wash-out" in label:
            code = "CTTerm_000143"
            subtype_uid = "CTTerm_000149"
        else:
            code = "CTTerm_000144"
            subtype_uid = "CTTerm_000147"

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
