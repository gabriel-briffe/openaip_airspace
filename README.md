# OpenAir Parser

This repository contains tools to fetch, validate, and convert OpenAir airspace files into standardized GeoJSON format.

## Overview

The pipeline processes OpenAir format airspace data from OpenAIP's Google Cloud Storage bucket, validates it, and converts it to GeoJSON format that can be used in mapping applications or other geospatial analysis.

## Processing Steps

1. Download OpenAir files from Google Cloud Storage
2. Validate files for correct syntax (`files_validation.py`)
3. Validate and correct block structures (`block_validation.py`)
4. Convert OpenAir to JSON format (`openair2json.py`)
5. Convert JSON to GeoJSON format (`json2geojson.py`)
6. Clean up temporary files after successful execution

## Usage

### Local Execution

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the processing pipeline:
   ```
   python process_airspace.py
   ```

The script will:
- Download specified airspace files from the OpenAIP Google Cloud Storage bucket
- Process them through the validation and conversion steps
- Create the `airspace.geojson` file
- Clean up all temporary files after successful execution (if an error occurs, temp files are preserved for debugging)

### GitHub Action

This repository is configured to run as a GitHub Action:
- It runs automatically every day at 2 AM UTC
- It can be triggered manually via the workflow_dispatch event
- The processed GeoJSON file is published as a GitHub release
- Each release is tagged with the date (e.g., `release-2023-04-04`)

### Accessing the Latest Airspace Data

The latest processed airspace data is available through GitHub releases. You can access it at this stable URL:

- Direct download link: `https://github.com/[username]/[repository]/releases/latest/download/airspace.geojson`

This URL will always point to the most recent release, making it suitable for integration with external applications.

## File Structure

- `temp/` - Temporary directory containing all intermediate files (cleaned up after successful execution)
  - `openAirFiles/` - Raw OpenAir files downloaded from OpenAIP
  - `validatedOpenairFiles/` - Files after initial validation
  - `blockValidatedOpenairFiles/` - Files after block structure validation
  - `json/` - Intermediate JSON representation
- `airspace.geojson` - Final GeoJSON output (only in the release, not in the repository)

## Scripts

- `process_airspace.py` - Main orchestration script
- `files_validation.py` - Validates OpenAir files syntax
- `block_validation.py` - Validates V blocks in OpenAir files
- `openair2json.py` - Converts OpenAir to JSON
- `json2geojson.py` - Converts JSON to GeoJSON 