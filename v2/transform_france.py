#!/usr/bin/env python3
import json
import os
import uuid
import re
import sys
from collections import defaultdict

# Import the is_standard_altitude_format function from analyze_geojson.py
from analyze_geojson import is_standard_altitude_format

# Import the convert_altitude_to_meters function from json2geojson.py
from json2geojson import convert_altitude_to_meters

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
    - upperLimitMeters = converted AH value in meters
    - lowerLimitMeters = converted AL value in meters
    
    Type Rules:
    - If class is E and name starts with "LTA " → type = E
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
        
        # Rule 1: If class is E and name starts with "LTA " → type = E
        name = props.get('name', '')
        if airspace_class == 'E' and name and name.startswith("LTA "):
            final_type = 'E'
        # Rule 2: If type is GSEC → type = GLIDING_SECTOR
        elif airspace_type == 'GSEC':
            final_type = 'GLIDING_SECTOR'
        # Rule 3: If type is AERIAL_SPORTING_RECREATIONAL → type = ACTIVITY
        elif airspace_type == 'AERIAL_SPORTING_RECREATIONAL':
            final_type = 'ACTIVITY'
        # Rule 4: If class is A, B, C, D, E, F, or G → type = class
        elif airspace_class and airspace_class in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            final_type = airspace_class
        # Rule 5: If type is P → type = PROHIBITED
        elif airspace_type == 'P':
            final_type = 'PROHIBITED'
        # Rule 6: If type is Q → type = DANGER
        elif airspace_type == 'Q':
            final_type = 'DANGER'
        # Rule 7: If type is R → type = RESTRICTED
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
                    lower_limit_str = f"{lower_ceiling_value}{upper_ceiling_unit} MSL"
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
            "type": final_type,                       # modified type according to rules
            "upperLimitMeters": convert_altitude_to_meters(upper_limit_str),  # converted AH value in meters
            "lowerLimitMeters": convert_altitude_to_meters(lower_limit_str)   # converted AL value in meters
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
    
    return True

def main():
    # Check for command line arguments
    if len(sys.argv) != 3:
        print("Usage: python transform_france.py <input_file> <output_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        sys.exit(1)
    
    # Transform the data
    print(f"\n===== Transforming France GeoJSON data =====")
    success = transform_france_airspace(input_file, output_file)
    
    if success:
        print("Transformation completed successfully.")
    else:
        print("Transformation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 