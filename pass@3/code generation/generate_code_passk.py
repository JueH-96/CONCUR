#!/usr/bin/env python3
import os
import sys
import subprocess
import csv
from pathlib import Path
import tempfile
import re


def write_result_to_csv(result_csv, custom_folder_name, model_name, status):
    file_exists = Path(result_csv).exists()
    with open(result_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Seq", "Topic", "Model Name", "Result"])

        # Find current max sequence number
        max_seq = 0
        if file_exists:
            with open(result_csv, newline='') as f_read:
                reader = csv.reader(f_read)
                next(reader, None)  # skip header
                for row in reader:
                    if row and row[0].isdigit():
                        max_seq = max(max_seq, int(row[0]))

        new_seq = max_seq + 1
        writer.writerow([new_seq, custom_folder_name, model_name, status])
        print(f"Result appended to: {result_csv}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python generate_java.py <custom_folder_name> <model_name> \"<prompt>\"")
        sys.exit(1)

    custom_folder_name = sys.argv[1]
    model_name = sys.argv[2]
    prompt = sys.argv[3]

    script_dir = Path(__file__).parent.resolve()
    result_csv = script_dir / "result.csv"

    for v in range(1, 4):
        output_dir = script_dir / f"examples/{model_name}/{custom_folder_name}V{v}"
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory exists: {output_dir}")


        if any(output_dir.glob("*.java")):
            print(f"Java file already exists in {output_dir}. Skipping generation.")
            status = "skipped_existing_file"
            write_result_to_csv(result_csv, custom_folder_name, model_name, status)
            continue


        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp.write(prompt)
            tmp_prompt_path = tmp.name

        max_retries = 50

        for attempt in range(1, max_retries + 1):
            print(f"Attempt {attempt} of {max_retries} to get Java code for V{v}...")


            try:
                response = subprocess.check_output(
                    ["ollama", "run", model_name],
                    stdin=open(tmp_prompt_path, "r"),
                    text=True
                )
            except subprocess.CalledProcessError:
                print("ollama command failed.")
                continue

            # Extract Java code block
            lines = response.splitlines()
            code_block = []
            inside_block = False
            for line in lines:
                if line.strip().startswith("```java"):
                    inside_block = True
                    continue
                elif line.strip() == "```":
                    inside_block = False
                    continue
                if inside_block:
                    code_block.append(line)

            if not code_block:
                print("No Java code block found. Retrying...")
                continue

            code_text = "\n".join(code_block)

            # Extract class name
            match = re.search(r"public\s+class\s+(\w+)", code_text)
            if not match:
                match = re.search(r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)", code_text)
            if not match:
                print("No class definition found. Retrying...")
                continue

            class_name = match.group(1)
            sanitized_class_name = class_name.replace(" ", "_")
            java_file_path = output_dir / f"{sanitized_class_name}.java"

            with open(java_file_path, "w") as f:
                f.write(code_text)

            # Fix braces if needed
            open_braces = code_text.count("{")
            close_braces = code_text.count("}")
            if open_braces > close_braces:
                with open(java_file_path, "a") as f:
                    f.write("}\n")

            print(f"Java file saved as: {java_file_path}")

            # Compile Java
            result = subprocess.run(
                ["javac", str(java_file_path)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("Compilation succeeded.")
                status = "success"
                write_result_to_csv(result_csv, custom_folder_name, model_name, status)
                break
            else:
                print(f"Compilation failed. Java file kept: {java_file_path}")
                # Do not delete file, do not write result
                break

        # Cleanup temp prompt
        Path(tmp_prompt_path).unlink(missing_ok=True)

    print("Generation completed for all 3 versions.")

# ----------------------------
if __name__ == "__main__":
    main()
