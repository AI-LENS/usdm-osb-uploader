from collections import defaultdict

import httpx

from ..settings import settings
from .osb_api import create_study_structure_study_epoch


async def create_study_epochs(study_designs: list, study_uid: str):
    epochs = study_designs[0].get("epochs", [])
    elements = study_designs[0].get("elements", [])
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.osb_base_url}/epochs/allowed-configs")
        if response.status_code == 200:
            allowed_configs = response.json()
            # print(allowed_configs)
    for index, epoc in enumerate(epochs):
        epoch_id = epoc.get("id")
        epoch_order = index
        description = epoc.get("description", "")
        label = epoc.get("name", "")  # noqa: F841
        idx = next(
            (
                i
                for i, elem in enumerate(elements)
                if elem.get("id")[-1] == epoch_id[-1]
            ),
            None,
        )
        if idx is not None:
            start_rule_dict = elements[idx].get("transitionStartRule")
            start_rule = start_rule_dict.get("text") if start_rule_dict else None
            end_rule_dict = elements[idx].get("transitionEndRule")
            end_rule = end_rule_dict.get("text") if end_rule_dict else None
        else:
            start_rule = None
            end_rule = None

        if label.lower() == "screening":
            epoch_type_codes = "C48262"
        elif label.lower() == "follow-up":
            epoch_type_codes = "C99158"
        else:
            epoch_type_codes = epoc.get("type", {}).get("code", "")

        if epoch_type_codes:
            headers = {"accept": "application/json, text/plain, */*"}
            async with httpx.AsyncClient() as client:
                epochs_codelist = await client.get(
                    f"{settings.osb_base_url}/ct/terms?codelist_uid=C99079&page_number=1&page_size=1000",  # TODO: hardcoded code
                    headers=headers,
                )
                if epochs_codelist.status_code == 200:
                    items = epochs_codelist.json().get("items", [])
                    grouped_epochs = defaultdict(list)
                    for epoc in allowed_configs:
                        try:
                            term = next(
                                term
                                for term in epochs_codelist.json().get("items", [])
                                if term.get("term_uid") == epoc.get("subtype")
                            )
                            definition = term.get("attributes", {}).get(
                                "definition", ""
                            )
                            grouped_epochs[epoc.get("type_name")].append({
                                "type": epoc.get("type"),
                                "type_name": epoc.get("type_name"),
                                "subtype": epoc.get("subtype"),
                                "subtype_name": epoc.get("subtype_name"),
                                "definition": definition,
                            })
                        except StopIteration:
                            pass

                    all_subtypes = [
                        item for sub_tps in grouped_epochs.values() for item in sub_tps
                    ]
                    for item in items:
                        if (
                            item.get("attributes", {}).get("concept_id", "")
                            == epoch_type_codes
                        ):
                            epoch_subtype = item.get("term_uid", "")
                            sponsor_name = (
                                item.get("name", {})
                                .get("sponsor_preferred_name", "")
                                .lower()
                            )
                            matching_cfg = next(
                                (
                                    cfg
                                    for cfg in all_subtypes
                                    if cfg["type_name"] == sponsor_name
                                ),
                                None,
                            )
                            # print(matching_cfg)
                            epoch_type = matching_cfg["type"] if matching_cfg else None

                            epochs_response = await create_study_structure_study_epoch(  # noqa: F841
                                study_uid=study_uid,
                                epoch_type=epoch_type,
                                epoch_subtype=epoch_subtype,
                                start_rule=start_rule,
                                end_rule=end_rule,
                                order=epoch_order + 1,
                                description=description,
                            )
    print("Epochs created successfully.")
