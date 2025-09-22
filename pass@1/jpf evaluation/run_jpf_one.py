#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Script directory
SCRIPT_DIR = Path(__file__).resolve().parent
JPF_CORE = SCRIPT_DIR / "jpf-core"
JPF_BIN = JPF_CORE / "bin" / "jpf"
JPF_SRC_EXAMPLES = JPF_CORE / "src" / "examples"
EXAMPLES_DIR = SCRIPT_DIR / "examples"

# Get all .jpf files
JPF_FILES = list(EXAMPLES_DIR.rglob("*.jpf"))
print(f"Found {len(JPF_FILES)} .jpf files")

for i, jpf_file in enumerate(JPF_FILES, 1):
    print(f"Processing file {i}: {jpf_file}")
    jpf_dir = jpf_file.parent

    # Skip if the directory contains any .txt files
    if any(jpf_dir.glob("*.txt")):
        print(f"Skipping {jpf_file} because directory {jpf_dir} already contains .txt files")
        continue

    jpf_base_name = jpf_file.name
    java_base_name = jpf_file.stem + ".java"
    java_file = jpf_dir / java_base_name

    if not java_file.exists():
        print(f"Skipping {jpf_file} because corresponding {java_base_name} not found")
        continue

    # Copy files to jpf-core/src/examples
    try:
        shutil.copy(java_file, JPF_SRC_EXAMPLES)
        shutil.copy(jpf_file, JPF_SRC_EXAMPLES)
    except Exception as e:
        print(f"Failed to copy files: {e}")
        continue

    # Build JPF project
    print(f"Building: {java_base_name}")
    try:
        subprocess.run(
            ["./gradlew", "clean"],
            cwd=JPF_CORE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            ["./gradlew", "buildJar"],
            cwd=JPF_CORE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        error_log = jpf_dir / f"{timestamp}_{jpf_file.stem}_build_failed.txt"
        with open(error_log, "w") as f:
            f.write(f"Build failed: {java_base_name}\n")
            f.write(f"Skipping {java_base_name}\n")
        print(f"Build failed: {java_base_name}")
        # Clean up copied files
        (JPF_SRC_EXAMPLES / java_base_name).unlink(missing_ok=True)
        (JPF_SRC_EXAMPLES / jpf_base_name).unlink(missing_ok=True)
        continue

    # Output file path
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    output_file = jpf_dir / f"{timestamp}_{jpf_file.stem}.txt"

    print(f"Running JPF test: {jpf_base_name}")

    # Use relative path to run JPF
    rel_jpf_path = Path("../src/examples") / jpf_base_name

    try:
        subprocess.run(
            [JPF_BIN, str(rel_jpf_path)],
            cwd=JPF_BIN.parent,
            stdout=open(output_file, "w"),
            stderr=subprocess.STDOUT,
            check=True,
        )
        print(f"Success: {jpf_base_name}")
    except subprocess.CalledProcessError as e:
        print(f"Failed: {jpf_base_name} (Exit Code: {e.returncode})")

    # Clean up copied files
    (JPF_SRC_EXAMPLES / java_base_name).unlink(missing_ok=True)
    (JPF_SRC_EXAMPLES / jpf_base_name).unlink(missing_ok=True)

print(f"All JPF tests completed. Processed {len(JPF_FILES)} files.")
