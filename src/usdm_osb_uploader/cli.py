from cyclopts import App
from pydantic import FilePath
import json
from .osb.create_study import create_study_id
from .osb.high_level_design import create_study_high_level_design

cli = App()

@cli.command
async def create_study_uid(usdm_file: FilePath):
    """Create a study in the OSB system."""
    with open(usdm_file, "r") as f:
        usdm_data = json.load(f)
    study_uid = await create_study_id(usdm_data)
    return study_uid

def load_study_design(usdm_file: FilePath):
    with open(usdm_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    study_data = json_data.get("study", {})
    study_versions = study_data.get("versions", [])
    study_designs = study_versions[0].get("studyDesigns", [])
    return study_designs

@cli.command
async def create_study_properties(usdm_file: FilePath, study_uid: str):
    """Create a study properties in the OSB system."""
    study_designs = load_study_design(usdm_file)
    return await create_study_high_level_design(study_designs, study_uid)

    