#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-

import os
import csv
import re

def get_java_code(examples_dir, llm_name, problem_name):
    java_dir = os.path.join(examples_dir, llm_name, problem_name)
    if not os.path.isdir(java_dir):
        return ""
    for fname in os.listdir(java_dir):
        if fname.endswith(".java"):
            java_path = os.path.join(java_dir, fname)
            try:
                with open(java_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                print(f"Failed to read Java file: {java_path}, error: {e}")
    return ""

def analyze_examples_and_jpf_txt(writer, examples_dir):
    for llm_name in os.listdir(examples_dir):
        llm_path = os.path.join(examples_dir, llm_name)
        if not os.path.isdir(llm_path):
            continue

        for problem_name in os.listdir(llm_path):
            problem_path = os.path.join(llm_path, problem_name)
            if not os.path.isdir(problem_path):
                continue

            files = os.listdir(problem_path)
            has_jpf = any(f.endswith(".jpf") for f in files)
            txt_files = [f for f in files if f.endswith(".txt")]
            java_code = get_java_code(examples_dir, llm_name, problem_name)

            if txt_files:
                # Only process the latest txt file
                latest_txt_file = max(
                    txt_files,
                    key=lambda f: os.path.getmtime(os.path.join(problem_path, f))
                )
                txt_path = os.path.join(problem_path, latest_txt_file)

                try:
                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # Check depth limit
                    out_of_depth = "Y" if "depth limit reached:" in content else "N"
                    # Check time limit
                    out_of_time = "Y" if "Time limit exceeded, terminating search" in content else "N"

                    if has_jpf:
                        # NullPointerException classification
                        if "NullPointerException" in content:
                            result = "NPE"
                            thread_count = 0
                        else:
                            match = re.search(r"Unique logical threads created during execution:\s*(\d+)", content)
                            if match:
                                thread_count = int(match.group(1))
                                if thread_count == 1:
                                    result = "Single Thread"
                                elif "no errors detected" in content:
                                    result = "Pass JPF evaluation"
                                else:
                                    result = "Concurrency bug"
                            else:
                                thread_count = 0
                                result = "Concurrency bug"
                    else:
                        # If no jpf file exists, record as syntax error
                        result = "Syntax error"
                        thread_count = ""

                    writer.writerow([llm_name, problem_name, result, thread_count, java_code, out_of_depth, out_of_time])

                except Exception as e:
                    print(f"Error processing file {txt_path}: {e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Change to the examplesPass@1 folder if needed
    examples_dir = os.path.join(script_dir, "examples")
    output_dir = os.path.join(script_dir, "finalresult")
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, "finalresult.csv")

    with open(output_csv, mode="w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Large Language Model",
            "Problem Name",
            "Result",
            "Number of thread",
            "Generated Code",
            "Out of depth bound",
            "Out of time bound"
        ])
        analyze_examples_and_jpf_txt(writer, examples_dir)

if __name__ == "__main__":
    main()
