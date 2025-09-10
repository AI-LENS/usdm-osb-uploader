import json

from cyclopts import App
from pydantic import FilePath

from .osb.arms import create_study_arm
from .osb.create_study import create_study_id
from .osb.elements import create_study_element
from .osb.high_level_design import create_study_high_level_design
from .osb.objectivies_endpoints import create_study_objective_endpoint
from .osb.population import create_study_population

cli = App()


def load_study_design(usdm_file: FilePath):
    with open(usdm_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    return json_data


@cli.command
async def usdm_osb_uploader(usdm_file: FilePath):
    """Upload a USDM file to the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_uid = await create_study_id(usdm_data)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_high_level_design(study_designs, study_uid)
    await create_study_arm(study_designs, study_uid)
    await create_study_population(study_designs, study_uid)
    await create_study_objective_endpoint(study_designs, study_uid)
    await create_study_element(study_designs, study_uid)


@cli.command
async def create_study_uid(usdm_file: FilePath):
    """Create a study in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_uid = await create_study_id(usdm_data)
    return study_uid


@cli.command
async def create_study_properties(usdm_file: FilePath, study_uid: str):
    """Create a study properties in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    return await create_study_high_level_design(study_designs, study_uid)


@cli.command
async def create_study_arms(usdm_file: FilePath, study_uid: str):
    """Create study arms in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    arms_response = await create_study_arm(study_designs, study_uid)
    return arms_response


@cli.command
async def create_study_populations(usdm_file: FilePath, study_uid: str):
    """Create study population in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    population_response = await create_study_population(study_designs, study_uid)
    return population_response


@cli.command
async def create_study_objectives_endpoints(usdm_file: FilePath, study_uid: str):
    """Create study objectives and endpoints in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    objectives_response = await create_study_objective_endpoint(
        study_designs, study_uid
    )
    return objectives_response


@cli.command
async def create_study_elements(usdm_file: FilePath, study_uid: str):
    """Create study elements in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    elements_response = await create_study_element(study_designs, study_uid)
    return elements_response
