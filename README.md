# USDM OSB Uploader

## Overview
This project provides tools for uploading, processing, and managing USDM (Unified Study Data Model) study files for the CDISC OSB (Open Study Builder) platform. It includes CLI utilities and Python modules to automate study data ingestion and manipulation.

## Benefits
- **Automated Workflow**: Eliminates manual data entry and reduces human error in study setup
- **Time Savings**: Complete study upload in minutes instead of hours of manual configuration
- **Data Integrity**: Validates USDM structure and ensures consistent data mapping to OSB
- **Standardization**: Follows CDISC standards for seamless integration across platforms
- **Modular Architecture**: Independent modules for each study component (arms, epochs, visits, etc.) allowing flexible workflows
- **Type-Safe Operations**: Robust Pydantic schema validation ensures data integrity and API compatibility

## Robustness
- **Comprehensive Error Handling**: Graceful handling of API failures, network issues, and data validation errors
- **Retry Logic**: Automatic retry mechanisms for transient failures
- **Data Validation**: Pre-upload validation ensures USDM compliance before processing
- **Rollback Support**: Safe operations with ability to handle partial failures
- **Reliable Operations**: Comprehensive HTTP status code handling (400, 404, 409, 422, 500)

## Features
- **Complete Study Upload**: Upload entire USDM studies with comprehensive validation
- **Individual Components**: Create and manage specific study elements (arms, epochs, visits, criteria)
- **Data Processing**: Download and process study data from OSB
- **Activity Management**: Handle study activities and schedule of activities

## Installation

**Requirements:** Python 3.13+

1. Clone the repository:
```bash
git clone https://github.com/AI-LENS/usdm-osb-uploader.git
cd usdm-osb-uploader
```

2. Install dependencies:
```bash
uv sync
```


## Usage

### Complete Study Upload
```bash
uv run osb usdm-osb-uploader path/to/usdm_file.json
```

### Individual Components
```bash
# Create study
uv run osb create-study-uid path/to/usdm_file.json

# Study structure
uv run osb create-study-arms path/to/usdm_file.json STUDY_UID
uv run osb create-study-epochs-cmd path/to/usdm_file.json STUDY_UID
uv run osb create-study-visits-cmd path/to/usdm_file.json STUDY_UID

# Population & criteria
uv run osb create-study-populations path/to/usdm_file.json STUDY_UID
uv run osb create-study-criteria-cmd path/to/usdm_file.json STUDY_UID

# Download
uv run osb download-usdm-cmd STUDY_UID
```

### Configuration

```bash
export OSB_BASE_URL="https://your-osb-instance.com/api"
```


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For questions or issues, please open an issue on the GitHub repository.
