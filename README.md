# USDM OSB Uploader

## Overview
This project provides tools for uploading, processing, and managing USDM (Unified Study Data Model) study files for the CDISC OSB (Open Study Builder) platform. It includes CLI utilities and Python modules to automate study data ingestion and manipulation.

## Features
- Upload USDM JSON study files to OSB
- Download and process study data
- Modular tools for activities, arms, criteria, endpoints, and more

## Installation

Clone the project

```bash
 git clone https://github.com/AI-LENS/usdm-osb-uploader.git
```

Go to the project directory

```bash
  cd usdm-osb-uploader
```

Install dependencies

```bash
  uv sync
```


## Usage

### CLI Tool

Run the uploader from the command line:
```powershell
uv run osb usdm-osb-uploader .\dump\CDISC_Pilot_Study.json
```
Replace the JSON file path with your study file as needed.

## License

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) 

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For questions or issues, please open an issue on the GitHub repository.
