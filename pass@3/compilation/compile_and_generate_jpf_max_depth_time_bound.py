#!/usr/bin/env python3

import subprocess
import csv
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "examples"
GROUND_TRUTH_FILE = SCRIPT_DIR / "ground_truth.csv"

# Read ground_truth.csv and generate a mapping from Problem Name -> Max Depth
problem_depth = {}
with GROUND_TRUTH_FILE.open(newline='', encoding='utf-8-sig') as csvfile:
    reader = csv.DictReader(csvfile)

    # Clean column names
    fieldnames = [f.strip() for f in reader.fieldnames]
    field_map = {f.lower(): f for f in fieldnames}

    # Identify relevant columns
    problem_name_col = None
    max_depth_col = None
    for f in field_map:
        if 'problem' in f and 'name' in f:
            problem_name_col = field_map[f]
        if 'max' in f and 'depth' in f:
            max_depth_col = field_map[f]

    if not problem_name_col or not max_depth_col:
        raise ValueError("Cannot find 'Problem Name' or 'Max Depth' column in CSV")

    for row in reader:
        problem_name = row[problem_name_col].strip()
        max_depth = row[max_depth_col].strip()
        if max_depth.isdigit():
            problem_depth[problem_name] = int(max_depth)

print(f"Loaded ground truth for {len(problem_depth)} problems.")

# ================== Counters ==================
success_count = 0
fail_count = 0
fix_total = 0
fix_backticks = 0
fix_braces = 0

# Iterate over all Java files under examples
for java_file in OUTPUT_DIR.rglob("*.java"):

    try:
        lines = java_file.read_text(encoding="utf-8").splitlines()
        fixed = False

        # Remove trailing ``` if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
            fixed = True
            fix_backticks += 1
            print(f"Removed trailing ``` from {java_file}")

        # Check and fix unmatched braces
        open_braces = sum(line.count("{") for line in lines)
        close_braces = sum(line.count("}") for line in lines)
        if close_braces < open_braces:
            lines.append("}")
            fixed = True
            fix_braces += 1
            print(f"Added missing closing brace to {java_file}")

        if fixed:
            fix_total += 1
            java_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    except Exception as e:
        print(f"Could not process {java_file}: {e}")

    base_name = java_file.stem
    dir_of_java = java_file.parent
    jpf_file = java_file.with_suffix(".jpf")

    print(f"Compiling Java file: {java_file}")
    build_dir = dir_of_java / "build"
    build_dir.mkdir(exist_ok=True)

    # Compile using javac
    compile_cmd = ["javac", "-d", str(build_dir), str(java_file)]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    compile_error = result.stderr

    if result.returncode == 0:
        success_count += 1
        print("Compilation succeeded.")

        # Get package name to generate fully qualified class name
        package_name = ""
        with java_file.open(encoding="utf-8") as f:
            for line in f:
                if line.startswith("package "):
                    package_name = line.strip().split()[1].rstrip(";")
                    break
        target_class = f"{package_name}.{base_name}" if package_name else base_name

        # Match Max Depth based on parent directory and multiply by 10
        parent_dir_name = java_file.parent.name
        max_depth = problem_depth.get(parent_dir_name)
        depth_line = f"search.depth_limit = {max_depth * 10}" if max_depth else ""

        print(f"Generating JPF file for: {base_name}")
        with jpf_file.open("w", encoding="utf-8") as f:
            f.write(f"target={target_class}\n")
            f.write("+vm.fast.startup\n")
            f.write("listener=gov.nasa.jpf.listener.ThreadCountListener,gov.nasa.jpf.listener.TimeLimitListener\n")
            f.write("timeLimitMillis=900000\n")
            if depth_line:
                f.write(depth_line + "\n")

        print(f"JPF file created at: {jpf_file}")

    else:
        fail_count += 1
        print("Compilation failed.")

        # Generate a safe result filename based on relative path
        relative_path = java_file.parent.relative_to(OUTPUT_DIR)
        dirs = relative_path.parts
        level2_dir = dirs[-2] if len(dirs) >= 2 else ""
        level1_dir = dirs[-1] if len(dirs) >= 1 else ""
        clean_level2_dir = re.sub(r'\W+', '_', level2_dir)
        clean_level1_dir = re.sub(r'\W+', '_', level1_dir)
        result_filename = f"{clean_level2_dir}_{clean_level1_dir}_result.txt"
        result_file = dir_of_java / result_filename

        with result_file.open("w", encoding="utf-8") as f:
            f.write(f"Compilation failed for file: {java_file}\n")
            f.write("Error message:\n")
            f.write(compile_error)

        print(f"Full compile error written to: {result_file}")

# ================== Summary ==================
print("\nSummary Report:")
print(f"   Compiled successfully: {success_count}")
print(f"   Compilation failed:     {fail_count}")
print(f"   Files fixed total:      {fix_total}")
print(f"      Removed backticks:   {fix_backticks}")
print(f"      Added braces:        {fix_braces}")
print("All Java files processed.")
