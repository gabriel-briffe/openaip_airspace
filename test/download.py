#!/usr/bin/env python3
import os
import json
import requests
from google.cloud import storage

def download_from_url(url, destination_file_name):
    """Download a file from a URL to a local file."""
    try:
        # Using the same anonymous client approach as the main code
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(destination_file_name)), exist_ok=True)
        
        # Write the content to the file
        with open(destination_file_name, 'wb') as f:
            f.write(response.content)
        
        print(f"Downloaded file from {url} to {destination_file_name}")
        return True
    except Exception as e:
        print(f"Error downloading from {url}: {e}")
        return False

def main():
    # URL for the France GeoJSON file
    france_geojson_url = "https://planeur-net.github.io/airspace/france.geojson"
    
    # Local file to save to
    destination_file = "test/france.geojson"
    
    # Download the file
    success = download_from_url(france_geojson_url, destination_file)
    
    if success:
        # Verify it's valid JSON by loading it
        try:
            with open(destination_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Successfully verified {destination_file} as valid JSON")
            print(f"File size: {os.path.getsize(destination_file) / (1024*1024):.2f} MB")
        except json.JSONDecodeError as e:
            print(f"Error: File is not valid JSON: {e}")
        except Exception as e:
            print(f"Error opening or reading file: {e}")
    else:
        print("Failed to download the file.")

if __name__ == "__main__":
    main() 