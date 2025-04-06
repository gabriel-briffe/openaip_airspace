#!/usr/bin/env python3
import json
import os
import sys
import re
from collections import defaultdict

def is_standard_altitude_format(altitude_str):
    """Check if an altitude string follows one of the standard formats."""
    if not altitude_str:
        return False
    
    # Normalize for checking
    altitude = altitude_str.strip().upper()
    
    # Flight level: FL + digits
    if re.match(r'^FL\d+$', altitude):
        return True
    
    # GND
    if altitude == "GND":
        return True
    
    # UNLIMITED
    if altitude == "UNLIMITED":
        return True
    
    # Feet or meters above MSL: [number]FT MSL or [number]M MSL
    if re.match(r'^\d+(FT|M)\s+MSL$', altitude):
        return True
    
    # Feet or meters above GND: [number]FT GND or [number]M GND
    if re.match(r'^\d+(FT|M)\s+GND$', altitude):
        return True
        
    return False

def analyze_geojson(filepath):
    """Analyze a GeoJSON file and extract all relevant information."""
    print(f"\n===== Analyzing {os.path.basename(filepath)} =====")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        print(f"Found {len(features)} features")
        
        # Track values
        ac_values = set()
        type_values = set()
        ay_values = set()
        ah_values = set()
        al_values = set()
        non_standard_ah = {}
        non_standard_al = {}
        
        for feature in features:
            props = feature.get('properties', {})
            
            # Extract values
            if 'AC' in props:
                ac_values.add(props['AC'])
                
            if 'type' in props:
                type_values.add(props['type'])
                
            if 'AY' in props:
                ay_values.add(props['AY'])
                
            if 'AH' in props:
                ah_value = props['AH']
                ah_values.add(ah_value)
                
                # Check if it's a standard format
                if not is_standard_altitude_format(ah_value):
                    if ah_value not in non_standard_ah:
                        non_standard_ah[ah_value] = 0
                    non_standard_ah[ah_value] += 1
            
            if 'AL' in props:
                al_value = props['AL']
                al_values.add(al_value)
                
                # Check if it's a standard format
                if not is_standard_altitude_format(al_value):
                    if al_value not in non_standard_al:
                        non_standard_al[al_value] = 0
                    non_standard_al[al_value] += 1
        
        # Print summary
        print("\nAC (airspace class) values:")
        for value in sorted(ac_values):
            print(f"  - {value}")
            
        print("\ntype values:")
        for value in sorted(type_values):
            print(f"  - {value}")
            
        print("\nAY values:")
        for value in sorted(ay_values):
            print(f"  - {value}")
        
        # Print non-standard altitude formats
        if non_standard_ah:
            print("\nNon-standard AH (upper ceiling) formats found:")
            for value, count in sorted(non_standard_ah.items(), key=lambda x: x[1], reverse=True):
                print(f"  - '{value}' (found {count} times)")
        else:
            print("\nAll AH (upper ceiling) values follow standard formats")
            
        if non_standard_al:
            print("\nNon-standard AL (lower ceiling) formats found:")
            for value, count in sorted(non_standard_al.items(), key=lambda x: x[1], reverse=True):
                print(f"  - '{value}' (found {count} times)")
        else:
            print("\nAll AL (lower ceiling) values follow standard formats")
        
        return {
            'feature_count': len(features),
            'ac_values': ac_values,
            'type_values': type_values,
            'ay_values': ay_values,
            'ah_values': ah_values,
            'al_values': al_values,
            'non_standard_ah': non_standard_ah,
            'non_standard_al': non_standard_al
        }
    
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

def compare_geojson_files(file1_analysis, file2_analysis, file1_name, file2_name):
    """Compare analysis results from two GeoJSON files."""
    if not file1_analysis or not file2_analysis:
        print("\nCannot compare files because one or both analyses failed.")
        return
    
    print(f"\n===== Comparison between {file1_name} and {file2_name} =====")
    
    # Feature counts
    print(f"\nFeature counts:")
    print(f"  {file1_name}: {file1_analysis['feature_count']} features")
    print(f"  {file2_name}: {file2_analysis['feature_count']} features")
    
    # Compare AC values
    file1_ac = file1_analysis['ac_values']
    file2_ac = file2_analysis['ac_values']
    
    print(f"\nAC (airspace class) values:")
    print(f"  {file1_name}: {len(file1_ac)} unique values")
    print(f"  {file2_name}: {len(file2_ac)} unique values")
    
    common_ac = file1_ac.intersection(file2_ac)
    print(f"\nCommon AC values: {len(common_ac)}")
    for value in sorted(common_ac):
        print(f"  - {value}")
    
    file1_only_ac = file1_ac - file2_ac
    if file1_only_ac:
        print(f"\nAC values only in {file1_name}: {len(file1_only_ac)}")
        for value in sorted(file1_only_ac):
            print(f"  - {value}")
    
    file2_only_ac = file2_ac - file1_ac
    if file2_only_ac:
        print(f"\nAC values only in {file2_name}: {len(file2_only_ac)}")
        for value in sorted(file2_only_ac):
            print(f"  - {value}")
    
    # Compare type values
    file1_type = file1_analysis['type_values']
    file2_type = file2_analysis['type_values']
    
    print(f"\ntype values:")
    print(f"  {file1_name}: {len(file1_type)} unique values")
    print(f"  {file2_name}: {len(file2_type)} unique values")
    
    common_type = file1_type.intersection(file2_type)
    print(f"\nCommon type values: {len(common_type)}")
    for value in sorted(common_type):
        print(f"  - {value}")
    
    file1_only_type = file1_type - file2_type
    if file1_only_type:
        print(f"\ntype values only in {file1_name}: {len(file1_only_type)}")
        for value in sorted(file1_only_type):
            print(f"  - {value}")
    
    file2_only_type = file2_type - file1_type
    if file2_only_type:
        print(f"\ntype values only in {file2_name}: {len(file2_only_type)}")
        for value in sorted(file2_only_type):
            print(f"  - {value}")
    
    # Compare non-standard altitude formats
    file1_ns_ah = file1_analysis['non_standard_ah']
    file2_ns_ah = file2_analysis['non_standard_ah']
    
    file1_ns_al = file1_analysis['non_standard_al']
    file2_ns_al = file2_analysis['non_standard_al']
    
    if file1_ns_ah or file2_ns_ah:
        print("\nNon-standard AH formats comparison:")
        print(f"  {file1_name}: {len(file1_ns_ah)} non-standard formats")
        print(f"  {file2_name}: {len(file2_ns_ah)} non-standard formats")
    
    if file1_ns_al or file2_ns_al:
        print("\nNon-standard AL formats comparison:")
        print(f"  {file1_name}: {len(file1_ns_al)} non-standard formats")
        print(f"  {file2_name}: {len(file2_ns_al)} non-standard formats")

def main():
    # Check for command line arguments
    if len(sys.argv) != 3:
        print("Usage: python analyze_geojson.py <airspace_file> <france_transformed_file>")
        sys.exit(1)
        
    airspace_file = sys.argv[1]
    france_file = sys.argv[2]
    
    # Check if files exist
    if not os.path.exists(airspace_file):
        print(f"Error: File {airspace_file} does not exist.")
        sys.exit(1)
        
    if not os.path.exists(france_file):
        print(f"Error: File {france_file} does not exist.")
        sys.exit(1)
    
    # Analyze both files
    airspace_analysis = analyze_geojson(airspace_file)
    france_analysis = analyze_geojson(france_file)
    
    # Compare the analyses
    compare_geojson_files(
        airspace_analysis, 
        france_analysis, 
        os.path.basename(airspace_file), 
        os.path.basename(france_file)
    )

if __name__ == "__main__":
    main() 