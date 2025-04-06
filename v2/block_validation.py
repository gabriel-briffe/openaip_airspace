import os

# Define directories based on the temp structure
TEMP_DIR = "temp"
VALIDATED_DIR = os.path.join(TEMP_DIR, "validatedOpenairFiles")
BLOCK_VALIDATED_DIR = os.path.join(TEMP_DIR, "blockValidatedOpenairFiles")


def validate_and_correct(filepath: str):
    """
    Validate and correct V blocks in the file.
    
    Process the file line by line. A valid V block is defined as:
      - A single V line (for DA or DB blocks) followed by a geometry command (DA, DB, or DC).
        For DA/DB blocks, the single V line must be a "V X=" line; if so, use the current V D= value or default to "V D=+" if none exists.
      - Two V lines followed by a geometry command, where the first line starts with "V D=" and the second with "V X=".
      - If exactly two V lines are found and they are inverted (first "V X=" and second "V D="), the function reverses them and counts the inversion.

    Returns a tuple: (errors, inversion_count, corrected_lines)
    """
    errors = []
    inversion_count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.rstrip("\n") for line in f]
    
    corrected_lines = []
    i = 0
    current_v_d = "+"  # Default direction
    while i < len(lines):
        line = lines[i].strip()
        
        # Reset current_v_d when starting a new airspace section
        if line.startswith("AC"):
            current_v_d = "+"
            corrected_lines.append(line)
            i += 1
            continue
            
        if line.startswith("V"):
            v_block_indices = []
            start_index = i
            # Collect consecutive V lines
            while i < len(lines) and lines[i].lstrip().startswith("V"):
                v_line = lines[i].strip()
                # Update current_v_d if we encounter a V D= line
                if v_line.startswith("V D="):
                    current_v_d = v_line.split("=", 1)[1].strip()
                v_block_indices.append(i)
                i += 1
            # Check termination: next non-V line must be a geometry command
            if i < len(lines) and lines[i].lstrip().startswith(("DA", "DB", "DC")):
                geom_cmd = lines[i].lstrip().split()[0]
                if geom_cmd in ("DA", "DB"):
                    if len(v_block_indices) == 1:
                        # Only one V line: it must be a V X= line
                        v_line = lines[v_block_indices[0]].strip()
                        if not v_line.startswith("V X="):
                            errors.append(f"Invalid single-V block in {geom_cmd} block starting at line {v_block_indices[0] + 1}: expected a V X= line, got: {v_line}")
                        # Use current V D= value and then the V X= line
                        corrected_lines.append(f"V D={current_v_d}")
                        corrected_lines.append(v_line)
                    elif len(v_block_indices) == 2:
                        first_line = lines[v_block_indices[0]].strip()
                        second_line = lines[v_block_indices[1]].strip()
                        # If inverted, swap them
                        if first_line.startswith("V X=") and second_line.startswith("V D="):
                            lines[v_block_indices[0]], lines[v_block_indices[1]] = lines[v_block_indices[1]], lines[v_block_indices[0]]
                            inversion_count += 1
                        # After swap, first must be V D= and second V X=
                        first_line = lines[v_block_indices[0]].strip()
                        second_line = lines[v_block_indices[1]].strip()
                        if not (first_line.startswith("V D=") and second_line.startswith("V X=")):
                            errors.append(
                                f"Invalid V block starting at line {v_block_indices[0] + 1}: expected 'V D=' then 'V X=', but got:\n"
                                f"  Line {v_block_indices[0] + 1}: {first_line}\n"
                                f"  Line {v_block_indices[1] + 1}: {second_line}"
                            )
                        # Update current_v_d from the V D= line
                        if first_line.startswith("V D="):
                            current_v_d = first_line.split("=", 1)[1].strip()
                        for idx in v_block_indices:
                            corrected_lines.append(lines[idx])
                    else:
                        if len(v_block_indices) > 2:
                            errors.append(f"Too many V lines starting at line {v_block_indices[0] + 1}: expected 1 or 2 V lines, got {len(v_block_indices)}.")
                        for idx in v_block_indices:
                            corrected_lines.append(lines[idx])
                    corrected_lines.append(lines[i])  # Append the geometry command line
                    i += 1  # Skip geometry command line
                else:  # geom_cmd is "DC"
                    for idx in v_block_indices:
                        corrected_lines.append(lines[idx])
                    corrected_lines.append(lines[i])
                    i += 1
            else:
                errors.append(f"Incomplete V block starting at line {v_block_indices[0] + 1}: not terminated by a geometry command.")
                for idx in v_block_indices:
                    corrected_lines.append(lines[idx])
        else:
            corrected_lines.append(lines[i])
            i += 1
    
    return errors, inversion_count, corrected_lines


def main():
    directory = VALIDATED_DIR
    all_files = [f for f in os.listdir(directory) if f.endswith(".openair")]
    if not all_files:
        print("No parsed openair files found in", directory)
        return

    total_inversion_count = 0
    overall_errors = False
    for filename in all_files:
        filepath = os.path.join(directory, filename)
        print(f"Processing file: {filename}")
        errors, inversion_count, corrected_lines = validate_and_correct(filepath)
        total_inversion_count += inversion_count
        if errors:
            overall_errors = True
            print("Errors found in file:", filename)
            for err in errors:
                print("  ", err)
        else:
            print(f"All clear: V blocks are complete in {filename}. Inversions corrected: {inversion_count}")
        output_dir = BLOCK_VALIDATED_DIR
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_filepath = os.path.join(output_dir, filename)
        with open(output_filepath, 'w', encoding='utf-8') as out_file:
            out_file.write("\n".join(corrected_lines))
        print(f"Output written to {output_filepath}\n")

    if not overall_errors:
        print(f"All files passed the V block validation. Total inversions corrected: {total_inversion_count}")
    else:
        print(f"Some files have errors in V blocks. Total inversions corrected: {total_inversion_count}")


if __name__ == "__main__":
    main() 