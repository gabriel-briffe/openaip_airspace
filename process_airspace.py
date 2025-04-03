#!/usr/bin/env python3
import os
import subprocess
import shutil
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
                  "au_asp_extended.txt", "ch_asp_extended.txt"]

def download_public_file(bucket_name, source_blob_name, destination_file_name):
    """Downloads a public blob from the bucket."""
    storage_client = storage.Client.create_anonymous_client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(
        f"Downloaded public blob {source_blob_name} from bucket {bucket.name} to {destination_file_name}"
    )

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

def run_validation():
    """Run the files_validation.py script."""
    print("\nRunning initial file validation...")
    subprocess.run(["python", "files_validation.py"], check=True)

def run_block_validation():
    """Run the block_validation.py script."""
    print("\nRunning block validation...")
    subprocess.run(["python", "block_validation.py"], check=True)

def run_openair_to_json():
    """Run the openair2json.py script."""
    print("\nConverting validated OpenAir files to JSON...")
    subprocess.run(["python", "openair2json.py"], check=True)

def run_json_to_geojson():
    """Run the json2geojson.py script."""
    print("\nConverting JSON to GeoJSON...")
    subprocess.run(["python", "json2geojson.py"], check=True)

def cleanup_temp_directory():
    """Remove the temp directory and all its contents."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        print(f"\nCleaned up temporary directory: {TEMP_DIR}")

def main():
    print("Starting airspace processing pipeline...")
    
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
        
        # Step 4: Clean up temp directory after successful run
        cleanup_temp_directory()
        
        print("\nAirspace processing pipeline completed successfully!")
    except Exception as e:
        print(f"\nError in processing pipeline: {e}")
        print("Temporary files kept for debugging purposes.")
        raise

if __name__ == "__main__":
    main() 