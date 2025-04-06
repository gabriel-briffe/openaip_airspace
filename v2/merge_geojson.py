#!/usr/bin/env python3
import json
import os
import sys

def merge_geojson_files(main_file, france_file, output_file):
    """
    Merge the transformed France GeoJSON data into the main airspace.geojson file.
    
    Parameters:
    - main_file: Path to the main airspace.geojson file
    - france_file: Path to the transformed France GeoJSON file
    - output_file: Path to save the merged GeoJSON file
    
    Returns:
    - True if successful, False otherwise
    """
    print(f"\n===== Merging {os.path.basename(france_file)} into {os.path.basename(main_file)} =====")
    
    try:
        # Load the main airspace.geojson file
        with open(main_file, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
        
        # Load the transformed France GeoJSON file
        with open(france_file, 'r', encoding='utf-8') as f:
            france_data = json.load(f)
        
        # Get feature counts
        main_features_count = len(main_data.get('features', []))
        france_features_count = len(france_data.get('features', []))
        
        print(f"Main airspace file has {main_features_count} features")
        print(f"France transformed file has {france_features_count} features")
        
        # Extract features from both files
        main_features = main_data.get('features', [])
        france_features = france_data.get('features', [])
        
        # Combine features
        combined_features = main_features + france_features
        
        # Create merged data
        merged_data = {
            "type": "FeatureCollection",
            "features": combined_features
        }
        
        # Save the merged data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2)
        
        print(f"Merged data saved to {output_file}")
        print(f"Total features in merged file: {len(combined_features)}")
        
        return True
    
    except Exception as e:
        print(f"Error merging files: {e}")
        return False

def filter_fir_from_airspace(input_file, output_file):
    """
    Filter out airspaces where AY = FIR from the airspace.geojson file.
    
    Parameters:
    - input_file: Path to the input GeoJSON file
    - output_file: Path to save the filtered GeoJSON file
    
    Returns:
    - True if successful, False otherwise
    """
    print(f"\n===== Filtering FIR airspaces from {os.path.basename(input_file)} =====")
    
    try:
        # Load the GeoJSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get features
        features = data.get('features', [])
        original_count = len(features)
        
        # Filter out features where AY = FIR
        filtered_features = [
            feature for feature in features 
            if not (feature.get('properties', {}).get('AY') == 'FIR')
        ]
        
        filtered_count = len(filtered_features)
        removed_count = original_count - filtered_count
        
        print(f"Original feature count: {original_count}")
        print(f"Filtered feature count: {filtered_count}")
        print(f"Removed {removed_count} features with AY = FIR")
        
        # Create filtered data
        filtered_data = {
            "type": "FeatureCollection",
            "features": filtered_features
        }
        
        # Save the filtered data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2)
        
        print(f"Filtered data saved to {output_file}")
        
        return True
    
    except Exception as e:
        print(f"Error filtering file: {e}")
        return False

def keep_only_fis_sector_from_fr_asp(input_file, output_file):
    """
    Keep only airspaces where AY = FIS_SECTOR from the fr_asp file.
    
    Parameters:
    - input_file: Path to the input GeoJSON file
    - output_file: Path to save the filtered GeoJSON file
    
    Returns:
    - True if successful, False otherwise
    """
    print(f"\n===== Keeping only FIS_SECTOR airspaces from {os.path.basename(input_file)} =====")
    
    try:
        # Load the GeoJSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get features
        features = data.get('features', [])
        original_count = len(features)
        
        # Keep only features where AY = FIS_SECTOR
        filtered_features = [
            feature for feature in features 
            if feature.get('properties', {}).get('AY') == 'FIS_SECTOR'
        ]
        
        filtered_count = len(filtered_features)
        removed_count = original_count - filtered_count
        
        print(f"Original feature count: {original_count}")
        print(f"Filtered feature count: {filtered_count}")
        print(f"Removed {removed_count} features without AY = FIS_SECTOR")
        
        # Create filtered data
        filtered_data = {
            "type": "FeatureCollection",
            "features": filtered_features
        }
        
        # Save the filtered data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2)
        
        print(f"Filtered data saved to {output_file}")
        
        return True
    
    except Exception as e:
        print(f"Error filtering file: {e}")
        return False

def main():
    # Check for command line arguments
    if len(sys.argv) < 3:
        print("Usage options:")
        print("  python merge_geojson.py merge <main_file> <france_file> <output_file>")
        print("  python merge_geojson.py filter-fir <input_file> <output_file>")
        print("  python merge_geojson.py keep-fis <input_file> <output_file>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'merge':
        if len(sys.argv) != 5:
            print("Usage: python merge_geojson.py merge <main_file> <france_file> <output_file>")
            sys.exit(1)
        
        main_file = sys.argv[2]
        france_file = sys.argv[3]
        output_file = sys.argv[4]
        
        # Check if files exist
        if not os.path.exists(main_file):
            print(f"Error: File {main_file} does not exist.")
            sys.exit(1)
            
        if not os.path.exists(france_file):
            print(f"Error: File {france_file} does not exist.")
            sys.exit(1)
        
        # Merge the files
        success = merge_geojson_files(main_file, france_file, output_file)
        
        if success:
            print("Merging completed successfully.")
        else:
            print("Merging failed.")
            sys.exit(1)
    
    elif command == 'filter-fir':
        if len(sys.argv) != 4:
            print("Usage: python merge_geojson.py filter-fir <input_file> <output_file>")
            sys.exit(1)
        
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        
        # Check if file exists
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} does not exist.")
            sys.exit(1)
        
        # Filter the file
        success = filter_fir_from_airspace(input_file, output_file)
        
        if success:
            print("Filtering completed successfully.")
        else:
            print("Filtering failed.")
            sys.exit(1)
    
    elif command == 'keep-fis':
        if len(sys.argv) != 4:
            print("Usage: python merge_geojson.py keep-fis <input_file> <output_file>")
            sys.exit(1)
        
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        
        # Check if file exists
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} does not exist.")
            sys.exit(1)
        
        # Filter the file
        success = keep_only_fis_sector_from_fr_asp(input_file, output_file)
        
        if success:
            print("Filtering completed successfully.")
        else:
            print("Filtering failed.")
            sys.exit(1)
    
    else:
        print("Invalid command.")
        print("Usage options:")
        print("  python merge_geojson.py merge <main_file> <france_file> <output_file>")
        print("  python merge_geojson.py filter-fir <input_file> <output_file>")
        print("  python merge_geojson.py keep-fis <input_file> <output_file>")
        sys.exit(1)

if __name__ == "__main__":
    main() 