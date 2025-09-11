import json

from cyclopts import App
from pydantic import FilePath

from .osb.activities import create_study_activity
from .osb.arms import create_study_arm
from .osb.create_study import create_study_id
from .osb.criteria import create_study_criteria
from .osb.download_usdm import download_usdm
from .osb.elements import create_study_element
from .osb.epochs_visits_soa import create_epochs_visits_soa
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
    study_uid, study_id = await create_study_id(usdm_data)
    study_version = usdm_data.get("study", {}).get("versions", [])[0]
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_high_level_design(study_designs, study_uid)
    await create_study_arm(study_designs, study_uid)
    await create_study_population(study_designs, study_uid)
    await create_study_objective_endpoint(study_designs, study_uid)
    await create_study_element(study_designs, study_uid)
    await create_study_criteria(study_version, study_uid)
    await create_study_activity(study_version, study_uid, study_id)
    await create_epochs_visits_soa(study_designs, study_uid)
    await download_usdm(study_uid)


@cli.command
async def create_study_uid(usdm_file: FilePath):
    """Create a study in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_uid, study_id = await create_study_id(usdm_data)
    return study_uid, study_id


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
    await create_study_arm(study_designs, study_uid)


@cli.command
async def create_study_populations(usdm_file: FilePath, study_uid: str):
    """Create study population in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_population(study_designs, study_uid)


@cli.command
async def create_study_objectives_endpoints(usdm_file: FilePath, study_uid: str):
    """Create study objectives and endpoints in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_objective_endpoint(study_designs, study_uid)


@cli.command
async def create_study_elements(usdm_file: FilePath, study_uid: str):
    """Create study elements in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_element(study_designs, study_uid)


@cli.command
async def create_study_criteria_cmd(usdm_file: FilePath, study_uid: str):
    """Create study criteria in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_version = usdm_data.get("study", {}).get("versions", [])[0]
    await create_study_criteria(study_version, study_uid)


@cli.command
async def create_study_activities(usdm_file: FilePath, study_uid: str, study_id: str):
    """Create study activities in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_version = usdm_data.get("study", {}).get("versions", [])[0]
    await create_study_activity(study_version, study_uid, study_id)


@cli.command
async def create_study_epochs_visits_soa(usdm_file: FilePath, study_uid: str):
    """Create study epochs, visits and schedule of activities in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_epochs_visits_soa(study_designs, study_uid)


@cli.command
async def download_usdm_cmd(study_uid: str):
    """Download the USDM file from the OSB system."""
    return await download_usdm(study_uid)
