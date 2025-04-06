#!/usr/bin/env python3
import os
import subprocess
import shutil
import json
import uuid
import re
import requests
from google.cloud import storage
import datetime

# Define base temp directory
TEMP_DIR = "temp"

# Define directories within temp
RAW_DIR = os.path.join(TEMP_DIR, "openAirFiles")
VALIDATED_DIR = os.path.join(TEMP_DIR, "validatedOpenairFiles")
BLOCK_VALIDATED_DIR = os.path.join(TEMP_DIR, "blockValidatedOpenairFiles")
JSON_DIR = os.path.join(TEMP_DIR, "json")

# Define bucket information
BUCKET_NAME = "29f98e10-a489-4c82-ae5e-489dbcd4912f"
FILES_TO_FETCH = ["fr_asp_extended.txt", "it_asp_extended.txt", 
                  "at_asp_extended.txt", "ch_asp_extended.txt"]

# France GeoJSON URL
FRANCE_GEOJSON_URL = "https://planeur-net.github.io/airspace/france.geojson"

def download_public_file(bucket_name, source_blob_name, destination_file_name):
    """Downloads a public blob from the bucket."""
    storage_client = storage.Client.create_anonymous_client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(
        f"Downloaded public blob {source_blob_name} from bucket {bucket.name} to {destination_file_name}"
    )

def download_from_url(url, destination_file_name):
    """Download a file from a URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(destination_file_name)), exist_ok=True)
        
        with open(destination_file_name, 'wb') as f:
            f.write(response.content)
        
        print(f"Downloaded file from {url} to {destination_file_name}")
        return True
    except Exception as e:
        print(f"Error downloading from {url}: {e}")
        return False

def create_directories():
    """Create necessary directories if they don't exist."""
    for directory in [TEMP_DIR, RAW_DIR, VALIDATED_DIR, BLOCK_VALIDATED_DIR, JSON_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

def download_files():
    """Download airspace files from Google Cloud Storage."""
    print("Downloading airspace files...")
    for file_name in FILES_TO_FETCH:
        # Convert to .openair extension for downstream processing
        local_file = os.path.join(RAW_DIR, file_name.replace(".txt", ".openair"))
        download_public_file(BUCKET_NAME, file_name, local_file)
    print("All files downloaded successfully.")

def download_france_geojson():
    """Download the France GeoJSON file."""
    print("\nDownloading France GeoJSON file...")
    destination_file = os.path.join(TEMP_DIR, "france.geojson")
    success = download_from_url(FRANCE_GEOJSON_URL, destination_file)
    return success

def run_validation():
    """Run the files_validation.py script."""
    print("\nRunning initial file validation...")
    subprocess.run(["python", "files_validation.py"], check=True)

def run_block_validation():
    """Run the block_validation.py script."""
    print("\nRunning block validation with filtering...")
    subprocess.run(["python", "block_validation.py"], check=True)

def run_openair_to_json():
    """Run the openair2json.py script."""
    print("\nConverting validated OpenAir files to JSON...")
    subprocess.run(["python", "openair2json.py"], check=True)

def run_json_to_geojson():
    """Run the json2geojson.py script."""
    print("\nConverting JSON to GeoJSON...")
    subprocess.run(["python", "json2geojson.py"], check=True)

def transform_france_geojson():
    """Transform France GeoJSON to match airspace.geojson structure."""
    print("\nTransforming France GeoJSON...")
    france_file = os.path.join(TEMP_DIR, "france.geojson")
    france_transformed_file = os.path.join(TEMP_DIR, "france_transformed.geojson")
    subprocess.run(["python", "transform_france.py", france_file, france_transformed_file], check=True)
    return france_transformed_file

def analyze_geojson_files():
    """Analyze airspace.geojson and france_transformed.geojson."""
    print("\nAnalyzing GeoJSON files...")
    airspace_file = "airspace.geojson"
    france_transformed_file = os.path.join(TEMP_DIR, "france_transformed.geojson")
    subprocess.run(["python", "analyze_geojson.py", airspace_file, france_transformed_file], check=True)

def merge_geojson_files():
    """Merge france_transformed.geojson into airspace.geojson."""
    print("\nMerging GeoJSON files...")
    airspace_file = "airspace.geojson"
    france_transformed_file = os.path.join(TEMP_DIR, "france_transformed.geojson")
    merged_file = "airspace_with_france.geojson"
    
    try:
        # Load airspace.geojson
        with open(airspace_file, 'r', encoding='utf-8') as f:
            airspace_data = json.load(f)
        
        # Load france_transformed.geojson
        with open(france_transformed_file, 'r', encoding='utf-8') as f:
            france_data = json.load(f)
        
        # Merge features
        airspace_data['features'].extend(france_data['features'])
        
        # Save merged file
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(merged_file)), exist_ok=True)
        with open(merged_file, 'w', encoding='utf-8') as f:
            json.dump(airspace_data, f, indent=2)
        
        print(f"Merged GeoJSON saved to {merged_file}")
        
        return True
    except Exception as e:
        print(f"Error merging GeoJSON files: {e}")
        return False

def main():
    print("Starting airspace processing pipeline v2...")
    
    # Step 1: Create directories
    create_directories()
    
    # Step 2: Download files
    download_files()
    
    # Step 3: Run the processing chain
    try:
        run_validation()
        run_block_validation()
        run_openair_to_json()
        run_json_to_geojson()
        
        # Step 4: Download and transform France GeoJSON
        france_success = download_france_geojson()
        if france_success:
            france_transformed_file = transform_france_geojson()
            
            # Step 5: Analyze GeoJSON files
            analyze_geojson_files()
            
            # Step 6: Merge GeoJSON files
            merge_success = merge_geojson_files()
            if not merge_success:
                print("Failed to merge GeoJSON files.")
        else:
            print("Failed to download France GeoJSON file. Skipping transformation and merge steps.")
        
        print("\nAirspace processing pipeline v2 completed successfully!")
        print(f"Note: Temporary directory {TEMP_DIR} has been preserved for debugging purposes.")
    except Exception as e:
        print(f"\nError in processing pipeline: {e}")
        print("Temporary files kept for debugging purposes.")
        raise

if __name__ == "__main__":
    main() 