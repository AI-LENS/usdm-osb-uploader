import json

from cyclopts import App
from pydantic import FilePath
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from .osb.activities import create_study_activity
from .osb.arms import create_study_arm
from .osb.create_study import create_study_id
from .osb.criteria import create_study_criteria
from .osb.download_usdm import download_usdm
from .osb.elements import create_study_element
from .osb.epochs import create_study_epochs
from .osb.high_level_design import create_study_high_level_design
from .osb.objectivies_endpoints import create_study_objective_endpoint
from .osb.population import create_study_population
from .osb.soa import create_schedule_of_activity
from .osb.visits import create_study_visits

cli = App()
console = Console()


def load_study_design(usdm_file: FilePath):
    with open(usdm_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    return json_data


@cli.command
async def usdm_osb_uploader(usdm_file: FilePath):
    """Upload a USDM file to the OSB system."""
    usdm_data = load_study_design(usdm_file)

    # Define all the steps with their descriptions
    steps = [
        ("Loading study data", lambda: None),
        ("Creating study ID", lambda: create_study_id(usdm_data)),
        (
            "Creating high level design",
            lambda: create_study_high_level_design(study_designs, study_uid),
        ),
        ("Creating study arms", lambda: create_study_arm(study_designs, study_uid)),
        (
            "Creating study epochs",
            lambda: create_study_epochs(study_designs, study_uid),
        ),
        (
            "Creating study elements",
            lambda: create_study_element(study_designs, study_uid),
        ),
        (
            "Creating study visits",
            lambda: create_study_visits(study_designs, study_uid),
        ),
        (
            "Creating study populations",
            lambda: create_study_population(study_designs, study_uid),
        ),
        (
            "Creating study criteria",
            lambda: create_study_criteria(study_version, study_uid),
        ),
        (
            "Creating objectives & endpoints",
            lambda: create_study_objective_endpoint(study_designs, study_uid),
        ),
        (
            "Creating study activities",
            lambda: create_study_activity(study_version, study_uid, study_id),
        ),
        (
            "Creating schedule of activities",
            lambda: create_schedule_of_activity(study_designs, study_uid),
        ),
        ("Downloading USDM", lambda: download_usdm(study_uid)),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        # Create overall progress task
        overall_task = progress.add_task("Overall Progress", total=len(steps))

        # Step 1: Load study data (already done)
        current_task = progress.add_task(steps[0][0], total=1)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 2: Create study ID
        current_task = progress.add_task(steps[1][0], total=1)
        study_uid, study_id = await create_study_id(usdm_data)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Prepare data for subsequent steps
        study_version = usdm_data.get("study", {}).get("versions", [])[0]
        study_designs = (
            usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
        )

        # Step 3: High level design
        current_task = progress.add_task(steps[2][0], total=1)
        await create_study_high_level_design(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 4: Study arms
        current_task = progress.add_task(steps[3][0], total=1)
        await create_study_arm(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 5: Study epochs
        current_task = progress.add_task(steps[4][0], total=1)
        await create_study_epochs(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 6: Study elements
        current_task = progress.add_task(steps[5][0], total=1)
        await create_study_element(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 7: Study visits
        current_task = progress.add_task(steps[6][0], total=1)
        await create_study_visits(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 8: Study populations
        current_task = progress.add_task(steps[7][0], total=1)
        await create_study_population(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 9: Study criteria
        current_task = progress.add_task(steps[8][0], total=1)
        await create_study_criteria(study_version, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 10: Objectives & endpoints
        current_task = progress.add_task(steps[9][0], total=1)
        await create_study_objective_endpoint(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 11: Study activities
        current_task = progress.add_task(steps[10][0], total=1)
        await create_study_activity(study_version, study_uid, study_id)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 12: Schedule of activities
        current_task = progress.add_task(steps[11][0], total=1)
        await create_schedule_of_activity(study_designs, study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

        # Step 13: Download USDM
        current_task = progress.add_task(steps[12][0], total=1)
        await download_usdm(study_uid)
        progress.update(current_task, advance=1)
        progress.update(overall_task, advance=1)

    console.print("✅ [bold green]USDM upload completed successfully![/bold green]")


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
async def create_study_epochs_cmd(usdm_file: FilePath, study_uid: str):
    """Create study epochs in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_epochs(study_designs, study_uid)


@cli.command
async def create_study_visits_cmd(usdm_file: FilePath, study_uid: str):
    """Create study visits in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_study_visits(study_designs, study_uid)


@cli.command
async def create_soa(usdm_file: FilePath, study_uid: str):
    """Create schedule of activities in the OSB system."""
    usdm_data = load_study_design(usdm_file)
    study_designs = (
        usdm_data.get("study", {}).get("versions", [])[0].get("studyDesigns", [])
    )
    await create_schedule_of_activity(study_designs, study_uid)


@cli.command
async def download_usdm_cmd(study_uid: str):
    """Download the USDM file from the OSB system."""
    return await download_usdm(study_uid)
