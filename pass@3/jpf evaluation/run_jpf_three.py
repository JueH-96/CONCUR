#!/usr/bin/env python3
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re

SCRIPT_DIR = Path(__file__).resolve().parent
JPF_CORE = SCRIPT_DIR / "jpf-core"
JPF_BIN = JPF_CORE / "bin" / "jpf"
JPF_SRC_EXAMPLES = JPF_CORE / "src" / "examples"
EXAMPLES_DIR = SCRIPT_DIR / "examples"

def run_jpf_test(vx_dir: Path, jpf_file: Path, java_file: Path) -> bool:
    """Run JPF test and return whether it passed"""
    shutil.copy(java_file, JPF_SRC_EXAMPLES)
    shutil.copy(jpf_file, JPF_SRC_EXAMPLES)

    subprocess.run(["./gradlew", "buildJar"], cwd=JPF_CORE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    output_file = vx_dir / f"{timestamp}_{jpf_file.stem}.txt"

    # Run JPF without timeout
    subprocess.run([str(JPF_BIN), str(JPF_SRC_EXAMPLES / jpf_file.name)],
                   cwd=JPF_BIN.parent, stdout=open(output_file, "w"), stderr=subprocess.STDOUT)

    # Cleanup
    (JPF_SRC_EXAMPLES / java_file.name).unlink(missing_ok=True)
    (JPF_SRC_EXAMPLES / jpf_file.name).unlink(missing_ok=True)

    if not output_file.exists() or output_file.stat().st_size == 0:
        print(f"{vx_dir.name}: JPF output is empty")
        return False

    with output_file.open() as f:
        content = f.read()
    if "no errors detected" in content:
        print(f"{jpf_file.name} test passed, no errors")
        return True
    else:
        print(f"{jpf_file.name} test found errors")
        return False

problem_count = 0

# Iterate over large language models
for model_dir in sorted([d for d in EXAMPLES_DIR.iterdir() if d.is_dir()]):
    print(f"=== Processing model: {model_dir.name} ===")

    # Group VX versions by problem name
    problems = defaultdict(list)
    for vx_dir in [d for d in model_dir.iterdir() if d.is_dir()]:
        # Extract problem name (remove trailing Vx)
        match = re.match(r"(.+?)(V\d+)$", vx_dir.name)
        if match:
            problem_name = match.group(1)
        else:
            problem_name = vx_dir.name
        problems[problem_name].append(vx_dir)

    # Iterate over problems
    for problem_name, vx_dirs in problems.items():
        problem_count += 1
        print(f"=== Processing problem: {problem_name} ===")
        skip_remaining = False

        # Sort VX versions
        vx_dirs.sort(key=lambda d: d.name)

        for vx_dir in vx_dirs:
            if skip_remaining:
                print(f"Skipping {vx_dir.name} because problem already passed")
                continue

            # Find .jpf and .java files
            jpf_files = list(vx_dir.glob("*.jpf"))
            if not jpf_files:
                print(f"Missing .jpf file, skipping {vx_dir.name}")
                continue
            jpf_file = jpf_files[0]
            java_file = vx_dir / f"{jpf_file.stem}.java"
            if not java_file.exists():
                print(f"Missing .java file, skipping {vx_dir.name}")
                continue

            # Check existing TXT files
            txt_files = list(vx_dir.glob("*.txt"))
            if txt_files:
                txt_file = txt_files[0]
                with txt_file.open() as f:
                    content = f.read()
                if "no errors detected" in content:
                    print(f"Result file already exists with no errors, skipping remaining versions: {vx_dir.name}")
                    skip_remaining = True
                    continue
                else:
                    print(f"Result file exists but found errors, continue to next version: {vx_dir.name}")
                    continue

            # Run JPF test
            if run_jpf_test(vx_dir, jpf_file, java_file):
                print(f"{vx_dir.name} test passed, skipping remaining versions")
                skip_remaining = True
            else:
                print(f"{vx_dir.name} test failed, continue to next version")

print("All problems tested")
print(f"Total number of problems processed: {problem_count}")
