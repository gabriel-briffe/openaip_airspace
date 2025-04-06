# Airspace Processing Pipeline V2

This directory contains the V2 version of the airspace processing pipeline. The pipeline processes airspace data from various sources, including Google Cloud Storage and external URLs, to create a comprehensive airspace dataset in GeoJSON format.

## Pipeline Overview

The pipeline performs the following steps:

1. **File Download**:
   - Downloads public airspace files from Google Cloud Storage
   - Downloads the `france.geojson` file from an external URL

2. **Airspace Filtering**:
   - Removes airspaces where `AY = FIR` from all files
   - Keeps only airspaces where `AY = FIS_SECTOR` in the `fr_asp` file

3. **File Validation**:
   - Validates OpenAir files structure and syntax
   - Performs block validation to ensure consistency

4. **Format Conversion**:
   - Converts validated OpenAir files to JSON
   - Converts JSON to GeoJSON

5. **France Data Processing**:
   - Transforms the `france.geojson` file to match the structure of `airspace.geojson`
   - Applies specific type transformation rules

6. **Analysis and Comparison**:
   - Analyzes both `airspace.geojson` and the transformed France data
   - Compares property values, altitudes, and types between the datasets

7. **Merging**:
   - Merges the transformed France data into the main `airspace.geojson` file

## Scripts

The pipeline consists of the following scripts:

- `process_airspace.py`: Main script that orchestrates the entire pipeline
- `files_validation.py`: Validates syntax and structure of OpenAir files
- `block_validation.py`: Validates airspace blocks for consistency
- `openair2json.py`: Converts OpenAir files to JSON format
- `json2geojson.py`: Converts JSON files to GeoJSON format
- `transform_france.py`: Transforms France GeoJSON data to match airspace structure
- `analyze_geojson.py`: Analyzes and compares GeoJSON files
- `merge_geojson.py`: Provides utilities for merging and filtering GeoJSON files

## Usage

Run the main processing script:

```bash
python v2/process_airspace.py
```

Or run individual scripts for specific tasks:

```bash
# Transform France GeoJSON
python v2/transform_france.py france.geojson france_transformed.geojson

# Analyze GeoJSON files
python v2/analyze_geojson.py airspace.geojson france_transformed.geojson

# Merge GeoJSON files
python v2/merge_geojson.py merge airspace.geojson france_transformed.geojson merged_airspace.geojson

# Filter out FIR airspaces
python v2/merge_geojson.py filter-fir input.geojson output.geojson

# Keep only FIS_SECTOR airspaces
python v2/merge_geojson.py keep-fis input.geojson output.geojson
```

## Directory Structure

During processing, the following directory structure is created:

```
v2/
├── temp/
│   ├── openAirFiles/           # Raw downloaded OpenAir files
│   ├── validatedOpenairFiles/  # Validated OpenAir files
│   ├── blockValidatedOpenairFiles/ # Block-validated OpenAir files
│   ├── json/                   # JSON conversion output
│   ├── france.geojson          # Original France GeoJSON
│   └── france_transformed.geojson # Transformed France GeoJSON
├── README.md                  # This file
└── various Python scripts
```

## Output

The pipeline produces the following outputs:

- `airspace.geojson`: The main airspace data file (without France data)
- `france_transformed.geojson`: Transformed France airspace data
- `airspace_with_france.geojson`: Final merged airspace data

## Notes

- The pipeline requires Python 3.6+ and the following dependencies:
  - google-cloud-storage
  - requests
- Make sure the scripts have execution permissions (`chmod +x script.py`) 