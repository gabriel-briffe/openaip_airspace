import os
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Define directories based on the temp structure
TEMP_DIR = "temp"
RAW_DIR = os.path.join(TEMP_DIR, "openAirFiles")
VALIDATED_DIR = os.path.join(TEMP_DIR, "validatedOpenairFiles")

def is_comment_or_empty(line: str) -> bool:
    """Check if a line is empty or a comment."""
    line = line.strip()
    return not line or line.startswith('*')

def extract_command(line: str) -> Tuple[str, str]:
    """Extract command and content from a line."""
    # Remove comments if any
    if '*' in line:
        line = line.split('*')[0]
    line = line.strip()
    
    if not line:
        return '', ''
    
    # Split by first space
    parts = line.split(' ', 1)
    command = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else ''
    return command, content

def validate_coordinate(coord_str: str) -> Tuple[bool, str]:
    """Validate a coordinate string using strict regex with optional space before direction letters.
    Expected format: 'XX:XX:XX[.XXXX][N/S] <whitespace> X{1,3}:XX:XX[.XXXX][E/W]'.
    Latitude must have exactly 2 digits for degrees, minutes, and seconds can have decimals.
    Longitude can have 1 to 3 digits for degrees.
    Seconds are allowed to be 60. """
    pattern = r'^(\d{2}):(\d{2}):(\d{1,2})(?:\.(\d+))?\s*([NS])\s+(\d{1,3}):(\d{2}):(\d{1,2})(?:\.(\d+))?\s*([EW])$'
    m = re.match(pattern, coord_str)
    if not m:
        return False, f"Invalid coordinate format: {coord_str}"
    try:
        lat_deg = int(m.group(1))
        lat_min = int(m.group(2))
        lat_sec = float(m.group(3) + ('.' + m.group(4) if m.group(4) else ''))
        lon_deg = int(m.group(6))
        lon_min = int(m.group(7))
        lon_sec = float(m.group(8) + ('.' + m.group(9) if m.group(9) else ''))
    except ValueError:
        return False, f"Non-numeric values in coordinates: {coord_str}"

    if lat_deg > 90:
        return False, f"Latitude degrees must be between 0 and 90: {lat_deg}"
    if lat_min >= 60:
        return False, f"Latitude minutes must be less than 60: {lat_min}"
    if lat_sec > 60:
        return False, f"Latitude seconds must be less than or equal to 60: {lat_sec}"
    if lon_deg > 180:
        return False, f"Longitude degrees must be between 0 and 180: {lon_deg}"
    if lon_min >= 60:
        return False, f"Longitude minutes must be less than 60: {lon_min}"
    if lon_sec > 60:
        return False, f"Longitude seconds must be less than or equal to 60: {lon_sec}"
    
    return True, ""

def validate_dp_command(content: str, line_num: int) -> List[str]:
    """Validate DP (Direct Point) command format."""
    errors = []
    is_valid, error = validate_coordinate(content)
    if not is_valid:
        errors.append(f"Line {line_num}: {error}")
    return errors

def validate_db_command(content: str, line_num: int) -> List[str]:
    """Validate DB (Arc by two points) command format."""
    errors = []
    
    # Split into two coordinates
    coords = [c.strip() for c in content.split(',')]
    if len(coords) != 2:
        errors.append(f"Line {line_num}: DB command must have exactly two coordinates separated by comma")
        return errors
    
    # Validate each coordinate
    for i, coord in enumerate(coords):
        is_valid, error = validate_coordinate(coord)
        if not is_valid:
            errors.append(f"Line {line_num}: {error} in coordinate {i+1}")
    
    return errors

def validate_dc_command(content: str, line_num: int) -> List[str]:
    """Validate DC (Circle) command format."""
    errors = []
    try:
        radius = float(content)
        if radius <= 0:
            errors.append(f"Line {line_num}: Circle radius must be positive")
    except ValueError:
        errors.append(f"Line {line_num}: Invalid circle radius format: {content}")
    return errors

def validate_da_command(content: str, line_num: int) -> List[str]:
    """Validate DA (Arc) command format."""
    errors = []
    
    # Split into three numbers
    parts = [p.strip() for p in content.split(',')]
    if len(parts) != 3:
        errors.append(f"Line {line_num}: DA command must have exactly three numbers (radius,start,end)")
        return errors
    
    # Validate each number, start and end must be between 0 and 360
    try:
        radius, start, end = map(float, parts)
        if radius <= 0:
            errors.append(f"Line {line_num}: Arc radius must be positive")
        if start < 0 or start > 360:
            errors.append(f"Line {line_num}: Arc start angle must be between 0 and 360")
        if end < 0 or end > 360:
            errors.append(f"Line {line_num}: Arc end angle must be between 0 and 360")
    except ValueError:
        errors.append(f"Line {line_num}: Invalid number format in DA command: {content}")
    
    return errors

def validate_v_command(content: str, line_num: int) -> List[str]:
    """Validate V (Variable) command format."""
    errors = []
    
    if '=' not in content:
        errors.append(f"Line {line_num}: V command must contain '='")
        return errors
    
    parts = content.split('=', 1)
    var_type = parts[0].strip()
    var_value = parts[1].strip()
    
    if var_type == 'D':
        if var_value not in ['+', '-']:
            errors.append(f"Line {line_num}: Invalid direction value: {var_value} (must be + or -)")
    elif var_type == 'X':
        is_valid, error = validate_coordinate(var_value)
        if not is_valid:
            errors.append(f"Line {line_num}: {error}")
    else:
        errors.append(f"Line {line_num}: Invalid V command variable: {var_type}")
    
    return errors

def analyze_file(filepath: str) -> Dict:
    """Analyze a single file for command formats."""
    result = {
        'commands_found': set(),
        'errors': [],
        'line_count': 0,
        'valid_lines': 0,
        'command_counts': defaultdict(int),
        'error_types': defaultdict(int)  # Track types of errors
    }
    
    def process_file_content(f) -> Dict:
        """Process file content with given file object."""
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if is_comment_or_empty(line):
                continue
            
            result['line_count'] += 1
            command, content = extract_command(line)
            
            if not command:
                result['errors'].append(f"Line {line_num}: No command found")
                result['error_types']['no_command'] += 1
                continue
            
            result['commands_found'].add(command)
            result['command_counts'][command] += 1
            
            # Validate command format
            if command.startswith('A'):
                # Skip validation for A* commands (AC, AN, AL, etc.)
                result['valid_lines'] += 1
                continue
            
            errors = []
            if command == 'DP':
                errors = validate_dp_command(content, line_num)
            elif command == 'DB':
                errors = validate_db_command(content, line_num)
            elif command == 'DC':
                errors = validate_dc_command(content, line_num)
            elif command == 'DA':
                errors = validate_da_command(content, line_num)
            elif command == 'V':
                errors = validate_v_command(content, line_num)
            else:
                errors = [f"Line {line_num}: Unknown command: {command}"]
                result['error_types']['unknown_command'] += 1
            
            if errors:
                result['errors'].extend(errors)
                for error in errors:
                    if 'coordinate format' in error.lower():
                        result['error_types']['coordinate_format'] += 1
                    elif 'latitude' in error.lower():
                        result['error_types']['invalid_latitude'] += 1
                    elif 'longitude' in error.lower():
                        result['error_types']['invalid_longitude'] += 1
                    elif 'radius' in error.lower():
                        result['error_types']['invalid_radius'] += 1
                    elif 'direction' in error.lower():
                        result['error_types']['invalid_direction'] += 1
            else:
                result['valid_lines'] += 1
        return result
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return process_file_content(f)
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                return process_file_content(f)
        except Exception as e:
            result['errors'].append(f"Error reading file: {str(e)}")
            return result

def format_coordinate_str(coord_str: str) -> str:
    """Format a coordinate string to canonical form.
    For latitude: always DD:DD:DD with a single space and then N/S.
    For longitude: always DDD:DD:DD with a single space and then E/W.
    This function parses the coordinate and pads numbers as needed.
    Decimal seconds are rounded to the nearest integer.
    Example: '48:50:8.5N 7:2:5.7E' -> '48:50:09 N 007:02:06 E'."""
    pattern = r'^\s*(\d{1,3}):(\d{1,2}):(\d{1,2})(?:\.(\d+))?\s*([NS])\s+(\d{1,3}):(\d{1,2}):(\d{1,2})(?:\.(\d+))?\s*([EW])\s*$'
    m = re.match(pattern, coord_str)
    if not m:
        # If it doesn't match, return the string stripped of extra spaces
        return ' '.join(coord_str.split())
    try:
        lat_deg = int(m.group(1))
        lat_min = int(m.group(2))
        lat_sec = float(m.group(3) + ('.' + m.group(4) if m.group(4) else ''))
        lat_dir = m.group(5)
        lon_deg = int(m.group(6))
        lon_min = int(m.group(7))
        lon_sec = float(m.group(8) + ('.' + m.group(9) if m.group(9) else ''))
        lon_dir = m.group(10)
    except ValueError:
        return ' '.join(coord_str.split())
    
    # Round seconds to nearest integer
    lat_sec = round(lat_sec)
    lon_sec = round(lon_sec)
    
    formatted_lat = f"{lat_deg:02d}:{lat_min:02d}:{lat_sec:02d} {lat_dir}"
    formatted_lon = f"{lon_deg:03d}:{lon_min:02d}:{lon_sec:02d} {lon_dir}"
    return formatted_lat + " " + formatted_lon

def parse_airspace_file(input_filepath: str, output_filepath: str):
    """Parse an airspace.openair file and output a canonical formatted version.
    - Every Ax command is normalized by removing duplicate spaces.
    - Coordinate commands (DP, DB, V with X=) are reformatted using format_coordinate_str.
    - A blank line is added before any new AC command.
    - For DB commands, each coordinate is formatted and joined with a comma and space.
    - For DA commands, numbers are simply stripped and joined.
    """
    output_lines = []
    first_line = True
    # Try multiple encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    file_read = False
    for enc in encodings:
        try:
            with open(input_filepath, 'r', encoding=enc) as f:
                for line in f:
                    original_line = line.rstrip("\n")
                    # If the line is empty or a comment, normalize and output as is.
                    if is_comment_or_empty(original_line):
                        normalized = ' '.join(original_line.split())
                        output_lines.append(normalized)
                        continue
                    command, content = extract_command(original_line)
                    formatted_line = ""
                    if command == "AC":
                        if not first_line:
                            output_lines.append("")  # blank line before new AC command
                        formatted_line = ' '.join((command + " " + content).split())
                    elif command.startswith("A"):
                        formatted_line = ' '.join((command + " " + content).split())
                    elif command == "DP":
                        formatted_line = "DP " + format_coordinate_str(content)
                    elif command == "DB":
                        coords = [c.strip() for c in content.split(",")]
                        formatted_coords = [format_coordinate_str(coord) for coord in coords]
                        formatted_line = "DB " + ", ".join(formatted_coords)
                    elif command == "DC":
                        formatted_line = "DC " + ' '.join(content.split())
                    elif command == "DA":
                        parts = [p.strip() for p in content.split(",")]
                        formatted_line = "DA " + ", ".join(parts)
                    elif command == "V":
                        if content.lstrip().startswith("X"):
                            new_content = re.sub(r'\s*=\s*', '=', content)
                            coord = new_content[2:].strip()
                            formatted_line = "V X=" + format_coordinate_str(coord)
                        elif content.lstrip().startswith("D"):
                            new_content = re.sub(r'\s*=\s*', '=', content)
                            formatted_line = "V " + new_content
                        else:
                            formatted_line = "V " + ' '.join(content.split())
                    else:
                        formatted_line = ' '.join((command + " " + content).split())
                    output_lines.append(formatted_line)
                    first_line = False
            file_read = True
            break
        except UnicodeDecodeError:
            continue
    if not file_read:
        print(f"Error: Could not read {input_filepath} with supported encodings.")
        return
    
    with open(output_filepath, 'w', encoding='utf-8') as out_file:
        out_file.write("\n".join(output_lines))
    print(f"Parsed file written to {output_filepath}")

def main():
    directory = RAW_DIR
    all_results = {}
    all_commands = set()
    
    # Process each file
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            print(f"\nAnalyzing {filename}:")
            result = analyze_file(filepath)
            
            # Update all known commands
            all_commands.update(result['commands_found'])
            
            # Print analysis results for this file
            print(f"Total lines processed: {result['line_count']}")
            print(f"Valid lines: {result['valid_lines']}")
            print("Commands found:", sorted(result['commands_found']))
            print("\nCommand counts:")
            for cmd, count in sorted(result['command_counts'].items()):
                print(f"  {cmd}: {count}")
            
            print("\nError types:")
            for error_type, count in sorted(result['error_types'].items()):
                print(f"  {error_type}: {count}")
            
            if result['errors']:
                print("\nFirst 10 errors found:")
                for error in result['errors'][:10]:
                    print(f"  {error}")
                if len(result['errors']) > 10:
                    print(f"  ... and {len(result['errors']) - 10} more errors")
            
            # Store results
            all_results[filename] = result
            
            # Produce parsed output file in validatedOpenairFiles/ folder and if folder does not exist, create it   
            output_filename = os.path.splitext(filename)[0] + '.openair'
            if not os.path.exists(VALIDATED_DIR):
                os.makedirs(VALIDATED_DIR)
            output_filepath = os.path.join(VALIDATED_DIR, output_filename)
            parse_airspace_file(filepath, output_filepath)
    
    # Print overall summary
    print("\nOverall Summary:")
    print("All commands found across files:", sorted(all_commands))
    print("\nFiles processed:")
    for filename, result in all_results.items():
        print(f"\n{filename}:")
        print(f"  Lines: {result['line_count']}")
        print(f"  Valid: {result['valid_lines']}")
        print(f"  Error count: {len(result['errors'])}")
        if result['error_types']:
            print("  Error types:")
            for error_type, count in sorted(result['error_types'].items()):
                print(f"    {error_type}: {count}")

if __name__ == "__main__":
    main() 