import os
import re
import json

# Define directories based on the temp structure
TEMP_DIR = "temp"
BLOCK_VALIDATED_DIR = os.path.join(TEMP_DIR, "blockValidatedOpenairFiles")
JSON_DIR = os.path.join(TEMP_DIR, "json")

altitude_print_count = 0


def is_comment_or_empty(line: str) -> bool:
    line = line.strip()
    return not line or line.startswith('*')


def extract_command(line: str) -> (str, str):
    """Extracts the command and its content from a line."""
    # Remove comments
    if '*' in line:
        line = line.split('*')[0]
    line = line.strip()
    if not line:
        return '', ''
    parts = line.split(' ', 1)
    command = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else ''
    return command, content


def format_coordinate_str(coord_str: str) -> str:
    """Return the canonical formatted coordinate string (e.g., '48:50:08 N 007:02:05 E')"""
    pattern = r'^\s*(\d{1,3}):(\d{1,2}):(\d{1,2})\s*([NS])\s+(\d{1,3}):(\d{1,2}):(\d{1,2})\s*([EW])\s*$'
    m = re.match(pattern, coord_str)
    if not m:
        return ' '.join(coord_str.split())
    try:
        lat_deg = int(m.group(1))
        lat_min = int(m.group(2))
        lat_sec = int(m.group(3))
        lat_dir = m.group(4)
        lon_deg = int(m.group(5))
        lon_min = int(m.group(6))
        lon_sec = int(m.group(7))
        lon_dir = m.group(8)
    except ValueError:
        return ' '.join(coord_str.split())
    formatted_lat = f"{lat_deg:02d}:{lat_min:02d}:{lat_sec:02d} {lat_dir}"
    formatted_lon = f"{lon_deg:03d}:{lon_min:02d}:{lon_sec:02d} {lon_dir}"
    return formatted_lat + " " + formatted_lon


def parse_coordinate(coord_str: str) -> list:
    """Parse a coordinate string in DMS format (e.g., '48:50:08 N 007:02:05 E') and return [lon, lat] in decimal degrees."""
    # Use regex similar to format_coordinate_str
    pattern = r'^\s*(\d{1,3}):(\d{1,2}):(\d{1,2})\s*([NS])\s+(\d{1,3}):(\d{1,2}):(\d{1,2})\s*([EW])\s*$'
    m = re.match(pattern, coord_str)
    if not m:
        return None
    try:
        lat_deg = int(m.group(1))
        lat_min = int(m.group(2))
        lat_sec = int(m.group(3))
        lat_dir = m.group(4)
        lon_deg = int(m.group(5))
        lon_min = int(m.group(6))
        lon_sec = int(m.group(7))
        lon_dir = m.group(8)
    except ValueError:
        return None
    lat = lat_deg + lat_min/60 + lat_sec/3600
    lon = lon_deg + lon_min/60 + lon_sec/3600
    if lat_dir.upper() == 'S':
        lat = -lat
    if lon_dir.upper() == 'W':
        lon = -lon
    return [lon, lat]  # GeoJSON style


def parse_openair_file(filepath: str) -> list:
    """Parse an OpenAir file into a list of airspace features (blocks)."""
    features = []
    current_feature = None
    current_center = None  # from V X=
    current_direction = "+"

    def finalize_feature(feature):
        props = feature.get("properties", {})
        if "AC" in props and props["AC"] != "UNC":
            props["type"] = props["AC"]
        elif "AY" in props:
            props["type"] = props["AY"]
            if props["type"] == "OVERFLIGHT_RESTRICTION":
                props["type"] = "PROHIBITED"

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if is_comment_or_empty(line):
                continue
            command, content = extract_command(line)
            # Ax commands: those starting with A (e.g., AC, AN, AH, AL, AY, AF, AG)
            if command.startswith('A'):
                if command == 'AC':
                    if current_feature:
                        finalize_feature(current_feature)
                        features.append(current_feature)
                    current_feature = {"properties": {}, "geometry": []}
                    current_direction = "+"  # reset direction for new feature
                if current_feature is not None:
                    if command in ("AH", "AL"):
                        alt_content = content.strip().upper()
                        if "AMSL" in alt_content:
                            alt_content = alt_content.replace("AMSL", "MSL")
                        if "AGL" in alt_content:
                            alt_content = alt_content.replace("AGL", "GND")
                        if "SFC" in alt_content:
                            alt_content = alt_content.replace("SFC", "GND")
                        if " FT" in alt_content:
                            alt_content = alt_content.replace(" FT", "FT")
                        if " M" in alt_content:
                            alt_content = alt_content.replace(" M", "M")
                        if "FTMSL" in alt_content:
                            alt_content = alt_content.replace("FTMSL", "FT MSL")
                        if "MMSL" in alt_content:
                            alt_content = alt_content.replace("MMSL", "M MSL")
                        if "FTGND" in alt_content:
                            alt_content = alt_content.replace("FTGND", "FT GND")
                        if "MGND" in alt_content:
                            alt_content = alt_content.replace("MGND", "M GND")
                        if alt_content.startswith("FL "):
                            alt_content = alt_content.replace("FL ", "FL", 1)
                        # Remove leading zeros from flight level values
                        if alt_content.startswith("FL"):
                            fl_value = alt_content[2:]  # Get the value after "FL"
                            fl_value = str(int(fl_value))  # Convert to int and back to str to remove leading zeros
                            alt_content = "FL" + fl_value
                        if alt_content == "GND" or re.match(r'^\d+(FT|M)\s+MSL$', alt_content) or re.match(r'^\d+(FT|M)\s+GND$', alt_content) or re.match(r'^FL\d+$', alt_content):
                            formatted_altitude = alt_content
                        elif re.match(r'^\d+(FT|M)', alt_content):
                            formatted_altitude = alt_content+ " GND"
                        else:
                            formatted_altitude = alt_content  # placeholder for future formatting rules
                            global altitude_print_count
                            if altitude_print_count < 10:
                                print(f"Encountered {command}: {formatted_altitude}")
                                altitude_print_count += 1
                        current_feature["properties"][command] = formatted_altitude
                    else:
                        current_feature["properties"][command] = content.upper()
            elif command.startswith('V'):
                # Process V command. Handle center assignment (V X=) and direction (V D=)
                if content.lstrip().startswith('X='):
                    coord_val = content.split('=', 1)[1].strip()
                    formatted = format_coordinate_str(coord_val)
                    current_center = parse_coordinate(formatted)
                    if current_feature is not None:
                        current_feature["properties"]["V X"] = formatted.upper()
                elif content.lstrip().startswith('D='):
                    current_direction = content.split('=', 1)[1].strip()
                    if current_feature is not None:
                        current_feature["properties"]["V D"] = current_direction
            elif command in ('DP', 'DC', 'DA', 'DB'):
                if current_feature is None:
                    continue
                if command == 'DP':
                    # DP: polygon point, treat as individual point geometry
                    coord = parse_coordinate(content)
                    if coord:
                        current_feature["geometry"].append({"type": "point", "coordinates": coord})
                elif command == 'DC':
                    try:
                        radius = float(content.strip())
                    except ValueError:
                        radius = None
                    current_feature["geometry"].append({
                        "type": "circle", 
                        "radius": radius, 
                        "center": current_center})
                elif command == 'DA':
                    parts = [p.strip() for p in content.split(',')]
                    if len(parts) == 3:
                        try:
                            radius = float(parts[0])
                            start_angle = float(parts[1])
                            end_angle = float(parts[2])
                        except ValueError:
                            radius = start_angle = end_angle = None
                        current_feature["geometry"].append({
                            "type": "arc", "radius": radius, 
                            "start_angle": start_angle, 
                            "end_angle": end_angle, 
                            "center": current_center, 
                            "direction": current_direction})
                elif command == 'DB':
                    coords = [c.strip() for c in content.split(',')]
                    if len(coords) == 2:
                        p1 = parse_coordinate(coords[0])
                        p2 = parse_coordinate(coords[1])
                        current_feature["geometry"].append({
                            "type": "arc_by_points",
                            "start_point": p1,
                            "end_point": p2,
                            "center": current_center,
                            "direction": current_direction
                        })
            # else: ignore unknown commands
        if current_feature:
            finalize_feature(current_feature)
            features.append(current_feature)
    return features


def main():
    input_dir = BLOCK_VALIDATED_DIR
    output_dir = JSON_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".openair"):
            filepath = os.path.join(input_dir, filename)
            features = parse_openair_file(filepath)
            output_filename = os.path.splitext(filename)[0] + '.json'
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, 'w', encoding='utf-8') as out_file:
                json.dump(features, out_file, indent=2)
            print(f"Processed {filename} -> {output_filename}")


if __name__ == "__main__":
    main() 