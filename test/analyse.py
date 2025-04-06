#!/usr/bin/env python3
import json
import os
from collections import defaultdict

def extract_nested_keys(obj, prefix="", keys=None):
    """Extract all keys from a nested object, including nested dictionaries."""
    if keys is None:
        keys = set()
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            
            # Recursively process nested dictionaries
            if isinstance(value, dict):
                extract_nested_keys(value, full_key, keys)
            # Handle lists of dictionaries
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        extract_nested_keys(item, full_key, keys)
    
    return keys

def analyze_geojson(filepath):
    """Analyze a GeoJSON file and return information about its structure."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n====== Analysis for {filepath} ======")
        print(f"Successfully loaded {filepath}")
        
        # Check for GeoJSON type
        if 'type' in data:
            print(f"GeoJSON type: {data['type']}")
        else:
            print("Warning: No 'type' field found in the root object")
        
        # Analyze features if present
        if 'features' in data and isinstance(data['features'], list):
            feature_count = len(data['features'])
            print(f"Found {feature_count} features")
            
            # Analysis for each feature
            geometry_types = set()
            property_keys = set()
            nested_property_keys = set()
            property_key_counts = defaultdict(int)
            nested_key_counts = defaultdict(int)
            
            # For deeper analysis by property key
            property_values = defaultdict(set)
            
            for i, feature in enumerate(data['features']):
                # Check geometry type
                if 'geometry' in feature and 'type' in feature['geometry']:
                    geometry_types.add(feature['geometry']['type'])
                
                # Analyze properties - regular keys
                if 'properties' in feature and feature['properties']:
                    for key in feature['properties'].keys():
                        property_keys.add(key)
                        property_key_counts[key] += 1
                        
                        # Store some sample values for each property (limit to 10 samples)
                        if len(property_values[key]) < 10:
                            value = feature['properties'][key]
                            # Convert to string if it's a basic type
                            if isinstance(value, (str, int, float, bool)):
                                property_values[key].add(str(value))
                    
                    # Get nested keys
                    feature_nested_keys = extract_nested_keys(feature['properties'])
                    nested_property_keys.update(feature_nested_keys)
                    for key in feature_nested_keys:
                        nested_key_counts[key] += 1
            
            # Print geometry types found
            print("\nGeometry types found:")
            for gtype in sorted(geometry_types):
                print(f"  - {gtype}")
            
            # Print top-level property keys present
            print("\nTop-level property keys found:")
            for key in sorted(property_keys):
                presence_percentage = (property_key_counts[key] / feature_count) * 100
                print(f"  - {key} (present in {property_key_counts[key]}/{feature_count} features, {presence_percentage:.1f}%)")
            
            # Print all nested property keys
            print("\nAll property keys (including nested):")
            for key in sorted(nested_property_keys):
                presence_percentage = (nested_key_counts[key] / feature_count) * 100
                print(f"  - {key} (present in {nested_key_counts[key]}/{feature_count} features, {presence_percentage:.1f}%)")
            
            # Print some sample values for top-level property keys
            print("\nSample values for top-level property keys:")
            for key in sorted(property_keys):
                values_str = ", ".join(f"'{v}'" for v in list(property_values[key])[:5])
                if len(property_values[key]) > 5:
                    values_str += f" and {len(property_values[key]) - 5} more..."
                print(f"  - {key}: {values_str}")
                
            # Additional metadata
            print("\nAdditional metadata:")
            print(f"Total file size: {os.path.getsize(filepath) / (1024*1024):.2f} MB")
            
            # Check if all features have the same structure
            if len(data['features']) > 0:
                first_feature = data['features'][0]
                all_same = True
                
                for feature in data['features'][1:]:
                    if set(feature.keys()) != set(first_feature.keys()):
                        all_same = False
                        break
                    
                    if 'properties' in feature and 'properties' in first_feature:
                        if set(feature['properties'].keys()) != set(first_feature['properties'].keys()):
                            all_same = False
                            break
                
                if all_same:
                    print("All features have the same structure")
                else:
                    print("Features have varying structures")
                
            # Return the analysis results
            return {
                "feature_count": feature_count,
                "geometry_types": geometry_types,
                "property_keys": property_keys,
                "nested_property_keys": nested_property_keys,
                "property_key_counts": property_key_counts,
                "nested_key_counts": nested_key_counts
            }
        else:
            print("No 'features' array found in the GeoJSON")
            
            # Print root-level keys if not a standard GeoJSON
            print("\nRoot-level keys:")
            for key in data.keys():
                print(f"  - {key}")
            
            # Extract all keys from the entire document
            all_keys = extract_nested_keys(data)
            if all_keys:
                print("\nAll keys (including nested):")
                for key in sorted(all_keys):
                    print(f"  - {key}")
            
            return None
    
    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return None

def compare_analyses(france_analysis, airspace_analysis):
    """Compare the analysis results from two GeoJSON files."""
    if not france_analysis or not airspace_analysis:
        print("\nCannot compare analyses because one or both files could not be analyzed.")
        return
    
    print("\n====== Comparison of Property Keys ======")
    
    france_keys = france_analysis["property_keys"]
    airspace_keys = airspace_analysis["property_keys"]
    
    print(f"\nTop-level keys in france.geojson: {len(france_keys)}")
    print(f"Top-level keys in airspace.geojson: {len(airspace_keys)}")
    
    # Keys in both files
    common_keys = france_keys.intersection(airspace_keys)
    print(f"\nCommon top-level keys (in both files): {len(common_keys)}")
    for key in sorted(common_keys):
        print(f"  - {key}")
    
    # Keys only in france.geojson
    france_only_keys = france_keys - airspace_keys
    print(f"\nTop-level keys only in france.geojson: {len(france_only_keys)}")
    for key in sorted(france_only_keys):
        print(f"  - {key}")
    
    # Keys only in airspace.geojson
    airspace_only_keys = airspace_keys - france_keys
    print(f"\nTop-level keys only in airspace.geojson: {len(airspace_only_keys)}")
    for key in sorted(airspace_only_keys):
        print(f"  - {key}")
    
    # Now compare all nested keys
    france_nested_keys = france_analysis["nested_property_keys"]
    airspace_nested_keys = airspace_analysis["nested_property_keys"]
    
    print(f"\nAll keys (including nested) in france.geojson: {len(france_nested_keys)}")
    print(f"All keys (including nested) in airspace.geojson: {len(airspace_nested_keys)}")
    
    # Nested keys in both files
    common_nested_keys = france_nested_keys.intersection(airspace_nested_keys)
    print(f"\nCommon nested keys (in both files): {len(common_nested_keys)}")
    for key in sorted(common_nested_keys):
        print(f"  - {key}")
    
    # Nested keys only in france.geojson
    france_only_nested_keys = france_nested_keys - airspace_nested_keys
    print(f"\nNested keys only in france.geojson: {len(france_only_nested_keys)}")
    for key in sorted(france_only_nested_keys):
        print(f"  - {key}")
    
    # Nested keys only in airspace.geojson
    airspace_only_nested_keys = airspace_nested_keys - france_nested_keys
    print(f"\nNested keys only in airspace.geojson: {len(airspace_only_nested_keys)}")
    for key in sorted(airspace_only_nested_keys):
        print(f"  - {key}")
    
    # Compare geometry types
    print("\n====== Comparison of Geometry Types ======")
    france_geom = france_analysis["geometry_types"]
    airspace_geom = airspace_analysis["geometry_types"]
    
    print(f"Geometry types in france.geojson: {', '.join(sorted(france_geom))}")
    print(f"Geometry types in airspace.geojson: {', '.join(sorted(airspace_geom))}")

def main():
    # Path to the GeoJSON files
    france_filepath = "test/france.geojson"
    airspace_filepath = "test/airspace.geojson"
    
    files_exist = True
    
    # Check if files exist
    if not os.path.exists(france_filepath):
        print(f"Error: {france_filepath} does not exist. Please run download.py first.")
        files_exist = False
    
    if not os.path.exists(airspace_filepath):
        print(f"Error: {airspace_filepath} does not exist. Please copy it to the test directory.")
        files_exist = False
    
    if not files_exist:
        return
    
    # Analyze both files
    france_analysis = analyze_geojson(france_filepath)
    airspace_analysis = analyze_geojson(airspace_filepath)
    
    # Compare the analyses
    compare_analyses(france_analysis, airspace_analysis)

if __name__ == "__main__":
    main() 