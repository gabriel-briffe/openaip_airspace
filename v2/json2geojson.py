import os
import json
import math
import re

# Define directories based on the temp structure
TEMP_DIR = "temp"
JSON_DIR = os.path.join(TEMP_DIR, "json")


def circle_to_polygon(center, radius):
    """Convert a circle defined by center [lon, lat] and radius (in nautical miles) to a polygon (list of [lon, lat])."""
    if center is None or radius is None:
        return None
    lon_center, lat_center = center
    # 1 NM is approximately 1/60 degree of latitude
    r_deg_lat = radius / 60
    # Adjust for longitude: degrees per NM at given latitude
    r_deg_lon = r_deg_lat / math.cos(math.radians(lat_center)) if math.cos(math.radians(lat_center)) != 0 else 0
    num_segments = max(36, int(radius * 36))
    points = []
    for i in range(num_segments):
        angle_deg = 360 / num_segments * i
        angle_rad = math.radians(angle_deg)
        lon = lon_center + r_deg_lon * math.cos(angle_rad)
        lat = lat_center + r_deg_lat * math.sin(angle_rad)
        points.append([lon, lat])
    points.append(points[0])  # close the polygon
    return points


def process_arc(arc_geom):
    # Extract required values from the geometry
    start_angle = arc_geom.get("start_angle")
    end_angle = arc_geom.get("end_angle")
    center = arc_geom.get("center")
    radius = arc_geom.get("radius")
    direction = arc_geom.get("direction", "+")
    # Using provided 'direction' value for arc generation: '+' indicates clockwise, '-' indicates anticlockwise
    
    if start_angle is None or end_angle is None or center is None or radius is None:
        return []

    # Convert radius from nautical miles to an angular distance in radians
    d_rad = math.radians(radius / 60.0)

    center_lon, center_lat = center
    center_lat_rad = math.radians(center_lat)
    center_lon_rad = math.radians(center_lon)

    # Compute the start point using the destination point formula
    start_bearing_rad = math.radians(start_angle)
    start_lat_rad = math.asin(math.sin(center_lat_rad) * math.cos(d_rad) +
                              math.cos(center_lat_rad) * math.sin(d_rad) * math.cos(start_bearing_rad))
    start_lon_rad = center_lon_rad + math.atan2(math.sin(start_bearing_rad) * math.sin(d_rad) * math.cos(center_lat_rad),
                                                 math.cos(d_rad) - math.sin(center_lat_rad) * math.sin(start_lat_rad))
    start_point = [math.degrees(start_lon_rad), math.degrees(start_lat_rad)]

    # Compute the end point using the destination point formula
    end_bearing_rad = math.radians(end_angle)
    end_lat_rad = math.asin(math.sin(center_lat_rad) * math.cos(d_rad) +
                            math.cos(center_lat_rad) * math.sin(d_rad) * math.cos(end_bearing_rad))
    end_lon_rad = center_lon_rad + math.atan2(math.sin(end_bearing_rad) * math.sin(d_rad) * math.cos(center_lat_rad),
                                               math.cos(d_rad) - math.sin(center_lat_rad) * math.sin(end_lat_rad))
    end_point = [math.degrees(end_lon_rad), math.degrees(end_lat_rad)]

    # Build an arc_by_points geometry and call the corresponding function
    arc_by_points_geom = {
        "start_point": start_point,
        "end_point": end_point,
        "center": center,
        "direction": direction
    }

    return process_arc_by_points(arc_by_points_geom)


def process_arc_by_points(arc_by_points_geom):
    # Extract required values from the geometry
    start_point = arc_by_points_geom.get("start_point")
    end_point = arc_by_points_geom.get("end_point")
    center = arc_by_points_geom.get("center")
    direction = arc_by_points_geom.get("direction", "+")  # '+' for clockwise, '-' for anticlockwise
    # The 'direction' value is used below to adjust the computed delta angle

    if not start_point or not end_point or not center:
        return []

    # Unpack coordinates; note: format is [lon, lat]
    center_lon, center_lat = center
    start_lon, start_lat = start_point
    end_lon, end_lat = end_point

    # Convert degrees to radians
    center_lat_rad = math.radians(center_lat)
    center_lon_rad = math.radians(center_lon)
    start_lat_rad = math.radians(start_lat)
    start_lon_rad = math.radians(start_lon)
    end_lat_rad = math.radians(end_lat)
    end_lon_rad = math.radians(end_lon)

    # Compute angular radius from center to start_point (in radians) using spherical law of cosines
    radius = math.acos(
        math.sin(center_lat_rad) * math.sin(start_lat_rad) + 
        math.cos(center_lat_rad) * math.cos(start_lat_rad) * math.cos(start_lon_rad - center_lon_rad)
    )

    # Helper function to compute bearing from center to a given point
    def bearing_from_center(pt):
        pt_lon, pt_lat = pt
        pt_lat_rad = math.radians(pt_lat)
        pt_lon_rad = math.radians(pt_lon)
        dlon = pt_lon_rad - center_lon_rad
        y = math.sin(dlon) * math.cos(pt_lat_rad)
        x = math.cos(center_lat_rad) * math.sin(pt_lat_rad) - math.sin(center_lat_rad) * math.cos(pt_lat_rad) * math.cos(dlon)
        b = math.atan2(y, x)
        if b < 0:
            b += 2 * math.pi
        return b

    start_bearing = bearing_from_center(start_point)
    end_bearing = bearing_from_center(end_point)

    delta_angle = end_bearing - start_bearing
    # Adjust delta_angle based on direction: '+' means clockwise, '-' anticlockwise
    if direction == "+":
        if delta_angle < 0:
            delta_angle += 2 * math.pi
    else:
        if delta_angle > 0:
            delta_angle -= 2 * math.pi

    # Determine number of segments for the arc (excluding the endpoints)
    num_segments = max(2, int(abs(delta_angle) / math.radians(5)))
    arc_points = []

    # Compute intermediate points along the arc (excluding start and end points)
    for i in range(1, num_segments):
        t = i / num_segments
        bearing = start_bearing + t * delta_angle
        if bearing < 0:
            bearing += 2 * math.pi
        elif bearing > 2 * math.pi:
            bearing -= 2 * math.pi

        lat_rad = math.asin(math.sin(center_lat_rad) * math.cos(radius) + math.cos(center_lat_rad) * math.sin(radius) * math.cos(bearing))
        lon_rad = center_lon_rad + math.atan2(
            math.sin(bearing) * math.sin(radius) * math.cos(center_lat_rad),
            math.cos(radius) - math.sin(center_lat_rad) * math.sin(lat_rad)
        )
        lon_rad = (lon_rad + 3 * math.pi) % (2 * math.pi) - math.pi
        lat_point = math.degrees(lat_rad)
        lon_point = math.degrees(lon_rad)
        arc_points.append([lon_point, lat_point])

    # Include the official start and end points in the arc
    arc_points = [start_point] + arc_points + [end_point]

    return arc_points


def convert_geometry(geom):
    geom_type = geom.get("type")
    if geom_type == "point":
        return { "type": "Point", "coordinates": geom.get("coordinates") }
    elif geom_type == "circle":
        polygon = circle_to_polygon(geom.get("center"), geom.get("radius"))
        if polygon:
            return { "type": "Polygon", "coordinates": [polygon] }
    elif geom_type == "arc":
        coords = process_arc(geom)
        if coords:
            return { "type": "LineString", "coordinates": coords }
    elif geom_type == "arc_by_points":
        coords = process_arc_by_points(geom)
        if coords:
            return { "type": "LineString", "coordinates": coords }
    return None


def convert_altitude_to_meters(altitude_str):
    """Convert altitude string to meters.
    Handles formats like:
    - FL195 (Flight Level)
    - 3000FT MSL/GND (Feet above MSL/ground)
    - 1000M MSL/GND (Meters above MSL/ground)
    Returns None if conversion is not possible.
    """
    if not altitude_str:
        return None
    
    altitude_str = altitude_str.upper().strip()
    
    # Handle Flight Levels (FL)
    if altitude_str.startswith('FL'):
        try:
            fl_value = float(altitude_str[2:])
            return fl_value * 100 * 0.3048  # FL * 100 feet to meters
        except ValueError:
            return None
    
    # Handle ground level
    if altitude_str == 'GND':
        return 0
    
    # Extract numeric value and unit
    match = re.match(r'^(\d+)(FT|M)\s+(MSL|GND)$', altitude_str)
    if not match:
        return None
    
    value = float(match.group(1))
    unit = match.group(2)
    reference = match.group(3)
    
    # Convert to meters
    if unit == 'FT':
        value *= 0.3048
    # else unit is already meters
    
    return value


def convert_feature(feature):
    geometries = feature.get("geometry", [])
    properties = feature.get("properties", {})
    
    # Convert altitude limits to meters
    ah_value = properties.get("AH")
    al_value = properties.get("AL")
    
    upper_limit_meters = convert_altitude_to_meters(ah_value) if ah_value else None
    lower_limit_meters = convert_altitude_to_meters(al_value) if al_value else None
    
    # If there is exactly one geometry and it is not a point, use it directly
    if len(geometries) == 1:
        g = geometries[0]
        converted = convert_geometry(g)
        if converted and converted.get("type") != "Point":
            return {
                "type": "Feature",
                "properties": {
                    **properties,
                    "upperLimitMeters": upper_limit_meters,
                    "lowerLimitMeters": lower_limit_meters
                },
                "geometry": converted
            }
    
    # Otherwise, combine all coordinates from geometries (points and LineStrings) for a polygon
    coords = []
    for geom in geometries:
        converted = convert_geometry(geom)
        if not converted:
            continue
        typ = converted.get("type")
        if typ == "Point":
            coords.append(converted["coordinates"])
        elif typ == "LineString":
            # For LineString (arc_by_points) the returned coordinates are intermediate points
            coords.extend(converted["coordinates"])
        elif typ == "Polygon":
            # If a polygon is encountered (e.g., from a circle), use it directly
            coords = converted["coordinates"][0]
            break
    
    if len(coords) >= 3:
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        final_geom = { "type": "Polygon", "coordinates": [coords] }
    elif coords:
        final_geom = { "type": "MultiPoint", "coordinates": coords }
    else:
        final_geom = None
    
    return {
        "type": "Feature",
        "properties": {
            **properties,
            "upperLimitMeters": upper_limit_meters,
            "lowerLimitMeters": lower_limit_meters
        },
        "geometry": final_geom
    }


def remap_type_field(feature):
    """Remap type field values according to standardized naming conventions."""
    properties = feature.get("properties", {})
    if "type" in properties:
        type_value = properties["type"]
        
        # Define the remapping rules
        type_mapping = {
            "P": "PROHIBITED",
            "R": "RESTRICTED", 
            "Q": "DANGER",
            "ASRA": "ACTIVITY",
            "OFR": "PROHIBITED",
            "GSEC": "GLIDING_SECTOR"
        }
        
        # Apply remapping if the type value exists in our mapping
        if type_value in type_mapping:
            properties["type"] = type_mapping[type_value]
    
    return feature


def main():
    json_dir = JSON_DIR
    aggregated_features = []
    ac_set = set()
    ay_set = set()
    altitude_set = set()
    type_set = set()
    
    # Add tracking for filtering statistics
    total_features = 0
    filtered_features = 0
    filtering_reasons = {
        "FIR": 0,
        "fr_asp_non_FIS_SECTOR": 0
    }
    
    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(json_dir, filename)
            file_ac_set = set()
            file_ay_set = set()
            
            # Track file-specific stats
            file_total = 0
            file_filtered = 0
            
            # Check if this is a fr_asp file
            is_fr_asp = 'fr_asp' in filename.lower()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                features = json.load(f)
                file_total = len(features)
                total_features += file_total
                
                for feature in features:
                    properties = feature.get("properties", {})
                    
                    # Apply filtering rules
                    skip_feature = False
                    
                    # Rule 1: Skip features with AY=FIR
                    if "AY" in properties and "FIR" in properties["AY"]:
                        skip_feature = True
                        filtering_reasons["FIR"] += 1
                    
                    # Rule 2: For fr_asp files, keep only features with AY=FIS_SECTOR
                    if is_fr_asp and ("AY" not in properties or "FIS_SECTOR" not in properties["AY"]):
                        skip_feature = True
                        filtering_reasons["fr_asp_non_FIS_SECTOR"] += 1
                    
                    if skip_feature:
                        file_filtered += 1
                        filtered_features += 1
                        continue
                    
                    # Process features that pass the filters
                    if "AC" in properties:
                        ac_set.add(properties["AC"])
                        file_ac_set.add(properties["AC"])
                    if "AY" in properties:
                        ay_set.add(properties["AY"])
                        file_ay_set.add(properties["AY"])
                    if "type" in properties:
                        type_set.add(properties["type"])
                    for key in ["AH", "AL"]:
                        if key in properties:
                            altitude_value = re.sub(r'\d+', '', str(properties[key])).strip()
                            altitude_set.add(altitude_value)
                    
                    # Convert feature and apply type remapping
                    converted_feature = convert_feature(feature)
                    remapped_feature = remap_type_field(converted_feature)
                    aggregated_features.append(remapped_feature)
            
            # Report file-specific filtering stats
            print(f"\nFile: {filename}")
            print(f"  Features: {file_total} total, {file_filtered} filtered, {file_total - file_filtered} kept")
            print(f"  AC set: {sorted(file_ac_set) if file_ac_set else 'None'}")
            print(f"  AY set: {sorted(file_ay_set) if file_ay_set else 'None'}")
    
    # Create the GeoJSON output
    geojson = {
        "type": "FeatureCollection",
        "features": aggregated_features
    }
    output_file = "airspace.geojson"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2)
    
    # Report overall filtering stats
    features_kept = total_features - filtered_features
    filter_percentage = (filtered_features / total_features * 100) if total_features > 0 else 0
    
    print("\nFiltering Statistics:")
    print(f"  Total features: {total_features}")
    print(f"  Filtered out: {filtered_features} ({filter_percentage:.1f}%)")
    print(f"    - FIR airspaces: {filtering_reasons['FIR']}")
    print(f"    - fr_asp non-FIS_SECTOR: {filtering_reasons['fr_asp_non_FIS_SECTOR']}")
    print(f"  Features kept: {features_kept} ({100 - filter_percentage:.1f}%)")
    
    print("\nOverall sets:")
    print("AC set:", ac_set)
    print("AY set:", ay_set)
    print("Altitude set:", altitude_set)
    print("Type set:", sorted(type_set))
    print(f"GeoJSON written to {output_file} with {features_kept} features")


if __name__ == "__main__":
    main()
