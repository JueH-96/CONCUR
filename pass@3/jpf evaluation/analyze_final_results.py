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
                print(f" Cannot read Java File: {java_path}, Error: {e}")
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
                latest_txt_file = max(
                    txt_files,
                    key=lambda f: os.path.getmtime(os.path.join(problem_path, f))
                )
                txt_path = os.path.join(problem_path, latest_txt_file)

                try:
                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    if not has_jpf:
                        result = "Compilation failed"
                        thread_count = ""
                    else:
                        has_precise_race = "PreciseRaceDetector" in content

                        if "NullPointerException" in content and "====================================================== search finished" not in content:
                            result = "NPE"
                            thread_count = ""
                        elif "====================================================== search finished" not in content:
                            result = "Termination Error"
                            thread_count = 0
                        else:
                            match = re.search(r"Unique logical threads created during execution:\s*(\d+)", content)
                            if match:
                                thread_count = int(match.group(1))
                                if has_precise_race:
                                    result = "Race Condition"
                                elif thread_count == 1:
                                    result = "Single Thread"
                                elif "no errors detected" in content:
                                    result = "Passes"
                                else:
                                    result = "JPF Errors"
                            else:
                                thread_count = 0
                                result = "Race Condition" if has_precise_race else "JPF Errors"

                    writer.writerow([llm_name, problem_name, result, thread_count, java_code])

                except Exception as e:
                    print(f"Assessing {txt_path} wrong: {e}")

            else:
                writer.writerow([llm_name, problem_name, "No result", "", java_code])

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    examples_dir = os.path.join(script_dir, "examples")
    output_dir = os.path.join(script_dir, "finalresult")
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, "finalresult.csv")

    with open(output_csv, mode="w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Large Language Model", "Problem Name", "Result", "Number of thread", "Generated Code"])
        analyze_examples_and_jpf_txt(writer, examples_dir)

if __name__ == "__main__":
    main()

