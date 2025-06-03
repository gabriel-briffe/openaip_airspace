#!/usr/bin/env python3
import os
import subprocess
import shutil
import json
import uuid
import re
import requests
import hashlib
import sys
from google.cloud import storage
import datetime
from datetime import timezone

# Define base temp directory
TEMP_DIR = "temp"

# Define directories within temp
RAW_DIR = os.path.join(TEMP_DIR, "openAirFiles")
VALIDATED_DIR = os.path.join(TEMP_DIR, "validatedOpenairFiles")
BLOCK_VALIDATED_DIR = os.path.join(TEMP_DIR, "blockValidatedOpenairFiles")
JSON_DIR = os.path.join(TEMP_DIR, "json")

# Define bucket information
BUCKET_NAME = "29f98e10-a489-4c82-ae5e-489dbcd4912f"
FILES_TO_FETCH = ["fr_asp_v2.txt", "it_asp_v2.txt", 
                  "at_asp_v2.txt", "ch_asp_v2.txt"]

# France GeoJSON URL
FRANCE_GEOJSON_URL = "https://planeur-net.github.io/airspace/france.geojson"

# Checksums file
CHECKSUMS_FILE = "checksums.json"
CHECKSUMS_DOWNLOAD_URL = "https://github.com/gabriel-briffe/openaip_airspace/releases/latest/download/checksums.json"

def calculate_file_checksum(filepath):
    """Calculate SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    
    try:
        with open(filepath, "rb") as f:
            # Read and update hash in chunks for large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculating checksum for {filepath}: {e}")
        return None

def download_checksums_file():
    """Download the checksums file from the latest release."""
    print(f"Attempting to download previous checksums file from {CHECKSUMS_DOWNLOAD_URL}")
    try:
        response = requests.get(CHECKSUMS_DOWNLOAD_URL)
        if response.status_code == 200:
            with open(CHECKSUMS_FILE, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded checksums file from previous release")
            return True
        else:
            print(f"Failed to download checksums file: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading checksums file: {e}")
        return False

def load_checksums():
    """Load the saved checksums from the JSON file."""
    if os.path.exists(CHECKSUMS_FILE):
        try:
            with open(CHECKSUMS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading checksums file: {e}")
    return {}

def save_checksums(checksums):
    """Save the checksums to the JSON file."""
    try:
        with open(CHECKSUMS_FILE, 'w') as f:
            json.dump(checksums, f, indent=2)
        print(f"Checksums saved to {CHECKSUMS_FILE}")
    except Exception as e:
        print(f"Error saving checksums: {e}")

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
    """Download airspace files from Google Cloud Storage and calculate checksums."""
    print("Downloading airspace files...")
    
    # Track checksums for downloaded files
    current_checksums = {}
    
    for file_name in FILES_TO_FETCH:
        # Convert to .openair extension for downstream processing
        local_file = os.path.join(RAW_DIR, file_name.replace(".txt", ".openair"))
        download_public_file(BUCKET_NAME, file_name, local_file)
        
        # Calculate checksum for the downloaded file
        checksum = calculate_file_checksum(local_file)
        if checksum:
            current_checksums[file_name] = checksum
    
    print("All files downloaded successfully.")
    return current_checksums

def download_france_geojson(current_checksums):
    """Download the France GeoJSON file and calculate its checksum."""
    print("\nDownloading France GeoJSON file...")
    destination_file = os.path.join(TEMP_DIR, "france.geojson")
    success = download_from_url(FRANCE_GEOJSON_URL, destination_file)
    
    if success:
        # Calculate checksum
        checksum = calculate_file_checksum(destination_file)
        if checksum:
            current_checksums["france.geojson"] = checksum
    
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

def compare_checksums_intelligently(current_checksums, previous_checksums):
    """
    Intelligently compare checksums, handling filename changes gracefully.
    Returns (files_changed, comparison_details)
    """
    if not previous_checksums:
        return True, "No previous checksums available for comparison"
    
    files_changed = False
    comparison_details = []
    
    # Extract base filenames for intelligent matching
    def get_base_filename(filename):
        """Extract base filename for comparison (e.g., 'fr_asp_v2.txt' -> 'fr_asp')"""
        if filename == "france.geojson" or filename == "airspace_with_france.geojson":
            return filename
        # Remove common suffixes and extensions
        base = filename.replace("_extended", "").replace("_v2", "").replace(".txt", "")
        return base
    
    # Group current and previous files by base name
    current_by_base = {}
    previous_by_base = {}
    
    for filename, checksum in current_checksums.items():
        if filename != "metadata":
            base = get_base_filename(filename)
            current_by_base[base] = (filename, checksum)
    
    for filename, checksum in previous_checksums.items():
        if filename != "metadata":
            base = get_base_filename(filename)
            previous_by_base[base] = (filename, checksum)
    
    # Compare by base filename
    for base, (current_file, current_checksum) in current_by_base.items():
        if base in previous_by_base:
            previous_file, previous_checksum = previous_by_base[base]
            if current_checksum != previous_checksum:
                files_changed = True
                comparison_details.append(f"File {current_file} (was {previous_file}) has changed checksum")
            else:
                comparison_details.append(f"File {current_file} (was {previous_file}) unchanged")
        else:
            files_changed = True
            comparison_details.append(f"File {current_file} is new (no previous equivalent)")
    
    # Check for files that were removed
    for base, (previous_file, _) in previous_by_base.items():
        if base not in current_by_base:
            files_changed = True
            comparison_details.append(f"File {previous_file} was removed")
    
    return files_changed, comparison_details

def main():
    print("Starting airspace processing pipeline v2...")
    
    # Step 1: Create directories
    create_directories()
    
    # Step 2: Try to get previous checksums
    previous_checksums = {}
    downloaded_checksums = download_checksums_file()
    if downloaded_checksums:
        previous_checksums = load_checksums()
        print("Loaded previous checksums")
    else:
        print("No previous checksums available, will process files unconditionally")
    
    # Step 3: Download files and calculate checksums
    current_checksums = download_files()
    
    # Step 4: Download France GeoJSON
    france_success = download_france_geojson(current_checksums)
    if not france_success:
        print("Failed to download France GeoJSON file.")
        sys.exit(1)
    
    # Step 5: Compare checksums to determine if processing is needed
    files_changed, comparison_details = compare_checksums_intelligently(current_checksums, previous_checksums)
    
    # Print detailed comparison results
    print("\nChecksum comparison results:")
    for detail in comparison_details:
        print(f"  {detail}")
    
    if previous_checksums and not files_changed:
        print("\nNo input files have changed since the last run. Processing will be skipped.")
        # Create a marker file to indicate no changes
        with open("NO_CHANGES", "w") as f:
            f.write("No changes detected in input files, processing skipped.")
        sys.exit(0)
    elif not previous_checksums:
        print("No previous checksums available for comparison, will process all files")
    else:
        print(f"\nChanges detected, will process files")
    
    # Step 6: Process files
    print("\nProcessing files...")
    try:
        run_validation()
        run_block_validation()
        run_openair_to_json()
        run_json_to_geojson()
        
        # Step 7: Transform France GeoJSON
        france_transformed_file = transform_france_geojson()
        
        # Step 8: Analyze GeoJSON files
        analyze_geojson_files()
        
        # Step 9: Merge GeoJSON files
        merge_success = merge_geojson_files()
        if not merge_success:
            print("Failed to merge GeoJSON files.")
            sys.exit(1)
        
        # Step 10: Calculate checksum of the final output file
        final_checksum = calculate_file_checksum("airspace_with_france.geojson")
        if final_checksum:
            current_checksums["airspace_with_france.geojson"] = final_checksum
        
        # Add metadata to checksums
        current_checksums["metadata"] = {
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "version": "2.0"
        }
        
        # Step 11: Save checksums for the next run
        save_checksums(current_checksums)
        
        print("\nAirspace processing pipeline v2 completed successfully!")
        print(f"Note: Temporary directory {TEMP_DIR} has been preserved for debugging purposes.")
    except Exception as e:
        print(f"\nError in processing pipeline: {e}")
        print("Temporary files kept for debugging purposes.")
        raise

if __name__ == "__main__":
    main() 