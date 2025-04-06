#!/usr/bin/env python3
import json
import os
import uuid
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

def analyze_airspace_file(filepath):
    """Analyze airspace.geojson file to get sets of AC and type values"""
    ac_values = set()
    type_values = set()
    ay_values = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        print(f"\nAnalyzing {filepath}: {len(features)} features found")
        
        for feature in features:
            props = feature.get('properties', {})
            
            # Extract AC (airspace class)
            if 'AC' in props:
                ac_values.add(props['AC'])
            
            # Extract type
            if 'type' in props:
                type_values.add(props['type'])
                
            # Extract AY (might be similar to type)
            if 'AY' in props:
                ay_values.add(props['AY'])
        
        print(f"\nAC values in {os.path.basename(filepath)}:")
        for value in sorted(ac_values):
            print(f"  - {value}")
            
        print(f"\ntype values in {os.path.basename(filepath)}:")
        for value in sorted(type_values):
            print(f"  - {value}")
            
        print(f"\nAY values in {os.path.basename(filepath)}:")
        for value in sorted(ay_values):
            print(f"  - {value}")
        
        return {
            'ac_values': ac_values,
            'type_values': type_values,
            'ay_values': ay_values
        }
    
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

def transform_france_airspace(input_file, output_file):
    """
    Transform France GeoJSON airspace data to match the structure of the main airspace.geojson.
    
    Property Mapping:
    - AC = class 
    - AF = frequency.value
    - AG = frequency.name
    - AH = upperCeiling.value
    - AL = lowerCeiling.value
    - AI = generated UUID
    - AN = name
    - AY = type
    - type = modified type based on rules
    
    Type Rules:
    - If type is GSEC → type = GLIDING_SECTOR
    - If type is AERIAL_SPORTING_RECREATIONAL → type = ACTIVITY
    - If class is A, B, C, D, E, F, or G → type = class
    - If type is P → type = PROHIBITED
    - If type is Q → type = DANGER
    - If type is R → type = RESTRICTED
    """
    # Load the France GeoJSON file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            france_data = json.load(f)
    except Exception as e:
        print(f"Error loading {input_file}: {e}")
        return None
    
    # Initialize transformed data
    transformed_data = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Track values for AC property and type property
    ac_values = set()
    type_values = set()
    final_type_values = set()  # For tracking the transformed type values
    
    # Track non-standard altitude formats
    non_standard_ah = {}  # Maps non-standard AH values to count
    non_standard_al = {}  # Maps non-standard AL values to count
    
    # Process each feature
    for feature in france_data.get('features', []):
        props = feature.get('properties', {})
        
        # Extract values from nested properties
        upper_ceiling_value = None
        upper_ceiling_unit = None
        upper_ceiling_datum = None
        if 'upperCeiling' in props:
            upper_ceiling_value = props['upperCeiling'].get('value')
            upper_ceiling_unit = props['upperCeiling'].get('unit')
            upper_ceiling_datum = props['upperCeiling'].get('referenceDatum')
            
        lower_ceiling_value = None
        lower_ceiling_unit = None
        lower_ceiling_datum = None
        if 'lowerCeiling' in props:
            lower_ceiling_value = props['lowerCeiling'].get('value')
            lower_ceiling_unit = props['lowerCeiling'].get('unit')
            lower_ceiling_datum = props['lowerCeiling'].get('referenceDatum')
            
        frequency_value = None
        frequency_name = None
        if 'frequency' in props:
            frequency_value = props['frequency'].get('value')
            frequency_name = props['frequency'].get('name')
            
        # Get airspace class
        airspace_class = props.get('class')
        if airspace_class:
            ac_values.add(airspace_class)
            
        # Get airspace type
        airspace_type = props.get('type')
        if airspace_type:
            type_values.add(airspace_type)
        
        # Determine final type value based on the rules
        final_type = None
        
        # Rule 1: If type is GSEC → type = GLIDING_SECTOR
        if airspace_type == 'GSEC':
            final_type = 'GLIDING_SECTOR'
        # Rule 2: If type is AERIAL_SPORTING_RECREATIONAL → type = ACTIVITY
        elif airspace_type == 'AERIAL_SPORTING_RECREATIONAL':
            final_type = 'ACTIVITY'
        # Rule 3: If class is A, B, C, D, E, F, or G → type = class
        elif airspace_class and airspace_class in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            final_type = airspace_class
        # Rule 4: If type is P → type = PROHIBITED
        elif airspace_type == 'P':
            final_type = 'PROHIBITED'
        # Rule 5: If type is Q → type = DANGER
        elif airspace_type == 'Q':
            final_type = 'DANGER'
        # Rule 6: If type is R → type = RESTRICTED
        elif airspace_type == 'R':
            final_type = 'RESTRICTED'
        # Default: Use original type
        else:
            final_type = airspace_type
            
        if final_type:
            final_type_values.add(final_type)
        
        # Format AH (upper limit) value
        upper_limit_str = None
        if upper_ceiling_value is not None:
            if upper_ceiling_datum and upper_ceiling_unit:
                if upper_ceiling_datum == "STD":
                    upper_limit_str = f"FL{upper_ceiling_value}"
                elif upper_ceiling_datum == "AMSL":
                    upper_limit_str = f"{upper_ceiling_value}{upper_ceiling_unit} MSL"
                elif upper_ceiling_datum == "AGL":
                    upper_limit_str = f"{upper_ceiling_value}{upper_ceiling_unit} GND"
                else:
                    upper_limit_str = f"{upper_ceiling_value}{upper_ceiling_unit} {upper_ceiling_datum}"
            elif upper_ceiling_value == "UNLIMITED" or upper_ceiling_value == "UNLTD":
                upper_limit_str = "UNLIMITED"
        
        # Format AL (lower limit) value
        lower_limit_str = None
        if lower_ceiling_value is not None:
            if lower_ceiling_datum and lower_ceiling_unit:
                if lower_ceiling_datum == "STD":
                    lower_limit_str = f"FL{lower_ceiling_value}"
                elif lower_ceiling_datum == "AMSL":
                    lower_limit_str = f"{lower_ceiling_value}{lower_ceiling_unit} MSL"
                elif lower_ceiling_datum == "AGL":
                    lower_limit_str = f"{lower_ceiling_value}{lower_ceiling_unit} GND"
                elif lower_ceiling_datum == "SFC" or lower_ceiling_value == "GND":
                    lower_limit_str = "GND"
                else:
                    lower_limit_str = f"{lower_ceiling_value}{lower_ceiling_unit} {lower_ceiling_datum}"
            elif lower_ceiling_value == "GND" or lower_ceiling_value == "SFC":
                lower_limit_str = "GND"
        
        # Create new properties structure
        new_props = {
            "AC": airspace_class,                    # class
            "AF": frequency_value,                   # frequency.value
            "AG": frequency_name,                    # frequency.name
            "AH": upper_limit_str,                   # upperCeiling formatted
            "AL": lower_limit_str,                   # lowerCeiling formatted
            "AI": str(uuid.uuid4()),                 # generated unique ID
            "AN": props.get('name'),                 # name
            "AY": airspace_type,                     # original type
            "type": final_type                       # modified type according to rules
        }
        
        # Check for non-standard altitude formats
        if upper_limit_str and not is_standard_altitude_format(upper_limit_str):
            if upper_limit_str not in non_standard_ah:
                non_standard_ah[upper_limit_str] = 0
            non_standard_ah[upper_limit_str] += 1
            
        if lower_limit_str and not is_standard_altitude_format(lower_limit_str):
            if lower_limit_str not in non_standard_al:
                non_standard_al[lower_limit_str] = 0
            non_standard_al[lower_limit_str] += 1
        
        # Remove None values
        new_props = {k: v for k, v in new_props.items() if v is not None}
        
        # Create new feature
        new_feature = {
            "type": "Feature",
            "properties": new_props,
            "geometry": feature.get('geometry')
        }
        
        transformed_data["features"].append(new_feature)
    
    # Save the transformed data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=2)
        print(f"Transformed data saved to {output_file}")
    except Exception as e:
        print(f"Error saving {output_file}: {e}")
        return None
    
    print("\nSummary of france.geojson AC (airspace class) values:")
    for value in sorted(ac_values):
        print(f"  - {value}")
        
    print("\nSummary of france.geojson original type values:")
    for value in sorted(type_values):
        print(f"  - {value}")
        
    print("\nSummary of france.geojson transformed type values:")
    for value in sorted(final_type_values):
        print(f"  - {value}")
    
    # Report non-standard altitude formats
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
        'ac_values': ac_values,
        'type_values': type_values,
        'final_type_values': final_type_values,
        'non_standard_ah': non_standard_ah,
        'non_standard_al': non_standard_al
    }

def analyze_transformed_file(filepath):
    """Analyze altitude formats in the transformed file"""
    print(f"\n===== Analyzing altitude formats in {filepath} =====")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        features = data.get('features', [])
        
        # Track all AH and AL values
        ah_values = {}
        al_values = {}
        non_standard_ah = {}
        non_standard_al = {}
        
        for feature in features:
            props = feature.get('properties', {})
            
            # Check AH values
            if 'AH' in props:
                ah_value = props['AH']
                if ah_value not in ah_values:
                    ah_values[ah_value] = 0
                ah_values[ah_value] += 1
                
                # Check if it's a standard format
                if not is_standard_altitude_format(ah_value):
                    if ah_value not in non_standard_ah:
                        non_standard_ah[ah_value] = 0
                    non_standard_ah[ah_value] += 1
            
            # Check AL values
            if 'AL' in props:
                al_value = props['AL']
                if al_value not in al_values:
                    al_values[al_value] = 0
                al_values[al_value] += 1
                
                # Check if it's a standard format
                if not is_standard_altitude_format(al_value):
                    if al_value not in non_standard_al:
                        non_standard_al[al_value] = 0
                    non_standard_al[al_value] += 1
        
        # Print summary of non-standard formats
        if non_standard_ah:
            print("\nNon-standard AH (upper ceiling) formats found in transformed file:")
            for value, count in sorted(non_standard_ah.items(), key=lambda x: x[1], reverse=True):
                print(f"  - '{value}' (found {count} times)")
        else:
            print("\nAll AH (upper ceiling) values in transformed file follow standard formats")
            
        if non_standard_al:
            print("\nNon-standard AL (lower ceiling) formats found in transformed file:")
            for value, count in sorted(non_standard_al.items(), key=lambda x: x[1], reverse=True):
                print(f"  - '{value}' (found {count} times)")
        else:
            print("\nAll AL (lower ceiling) values in transformed file follow standard formats")
            
        return {
            'ah_values': ah_values,
            'al_values': al_values,
            'non_standard_ah': non_standard_ah,
            'non_standard_al': non_standard_al
        }
            
    except Exception as e:
        print(f"Error analyzing altitude formats in {filepath}: {e}")
        return None

def compare_values(france_values, airspace_values):
    """Compare the values from both datasets"""
    if not france_values or not airspace_values:
        print("\nCannot compare values because one or both datasets could not be analyzed.")
        return
    
    # Compare AC values
    france_ac = france_values['ac_values']
    airspace_ac = airspace_values['ac_values']
    
    print("\n====== Comparison of AC (airspace class) values ======")
    print(f"France AC values: {len(france_ac)}")
    print(f"Airspace AC values: {len(airspace_ac)}")
    
    common_ac = france_ac.intersection(airspace_ac)
    print(f"\nCommon AC values: {len(common_ac)}")
    for value in sorted(common_ac):
        print(f"  - {value}")
    
    france_only_ac = france_ac - airspace_ac
    print(f"\nAC values only in France data: {len(france_only_ac)}")
    for value in sorted(france_only_ac):
        print(f"  - {value}")
    
    airspace_only_ac = airspace_ac - france_ac
    print(f"\nAC values only in Airspace data: {len(airspace_only_ac)}")
    for value in sorted(airspace_only_ac):
        print(f"  - {value}")
    
    # Compare type values
    france_final_type = france_values.get('final_type_values', set())
    if not france_final_type:
        france_final_type = france_values['type_values']  # Fallback
    
    airspace_type = airspace_values['type_values']
    
    print("\n====== Comparison of type values ======")
    print(f"France transformed type values: {len(france_final_type)}")
    print(f"Airspace type values: {len(airspace_type)}")
    
    common_type = france_final_type.intersection(airspace_type)
    print(f"\nCommon type values: {len(common_type)}")
    for value in sorted(common_type):
        print(f"  - {value}")
    
    france_only_type = france_final_type - airspace_type
    print(f"\nType values only in France data: {len(france_only_type)}")
    for value in sorted(france_only_type):
        print(f"  - {value}")
        
    airspace_only_type = airspace_type - france_final_type
    print(f"\nType values only in Airspace data: {len(airspace_only_type)}")
    for value in sorted(airspace_only_type):
        print(f"  - {value}")

def main():
    # File paths
    france_file = "test/france.geojson"
    output_file = "test/france_transformed.geojson"
    airspace_file = "test/airspace.geojson"
    
    files_exist = True
    
    # Check if input files exist
    if not os.path.exists(france_file):
        print(f"Error: {france_file} does not exist. Please run download.py first.")
        files_exist = False
    
    if not os.path.exists(airspace_file):
        print(f"Error: {airspace_file} does not exist. Please copy it to the test directory.")
        files_exist = False
    
    if not files_exist:
        return
    
    # Transform the France data
    print("\n===== Transforming France GeoJSON data =====")
    france_values = transform_france_airspace(france_file, output_file)
    
    # Analyze altitude formats in the transformed file
    analyze_transformed_file(output_file)
    
    # Analyze the main airspace file
    print("\n===== Analyzing main airspace.geojson =====")
    airspace_values = analyze_airspace_file(airspace_file)
    
    # Compare the values
    if france_values and airspace_values:
        compare_values(france_values, airspace_values)

if __name__ == "__main__":
    main() 