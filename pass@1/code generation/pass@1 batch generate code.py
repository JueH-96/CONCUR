#!/usr/bin/env python3
import subprocess
import os
import csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_CSV = os.path.join(SCRIPT_DIR, "models.csv")
PROBLEMS_CSV = os.path.join(SCRIPT_DIR, "problemlist.csv")
GENERATE_SCRIPT = os.path.join(SCRIPT_DIR, "generate_java.sh")

# Load model names from CSV
models = []
with open(MODELS_CSV, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        model_name = row["Large Language Model"].strip()
        if model_name:
            models.append(model_name)

# Load problem topics and prompts from CSV
problems = []
with open(PROBLEMS_CSV, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        topic = row["Topic"].strip()
        prompt = row["Prompt"].strip()
        if topic and prompt:
            problems.append((topic, prompt))

# Run generate_java.sh for each model and problem combination
for model in models:
    for topic, prompt in problems:
        print(f"Running: Model='{model}', Topic='{topic}'")
        try:
            subprocess.run(
                [GENERATE_SCRIPT, topic, model, prompt],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Execution failed for Model='{model}', Topic='{topic}': {e}")
        print()
