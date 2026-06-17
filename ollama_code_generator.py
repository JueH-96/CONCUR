#!/usr/bin/env python3
"""
Ollama Java Code Generator
Read models and prompts from CSV files, call Ollama to generate Java code.
"""

import csv
import json
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any


class OllamaCodeGenerator:
    def __init__(self, prompts_csv: str, models_csv: str, ground_truth_csv: str = None,
                 output_base_dir: str = None):
        self.prompts_csv = prompts_csv
        self.models_csv = models_csv
        self.ground_truth_csv = ground_truth_csv
        self.output_base_dir = output_base_dir if output_base_dir else os.path.join(os.getcwd(), "Generated_Code")
        self.models = []
        self.prompts = []
        self.ground_truth_map = {}  # Stores problem_name -> ground_truth
        self.max_depth_map = {}     # Stores problem_name -> max_depth

    def load_models(self):
        """Load the model list from models.csv"""
        print("Loading models from CSV...")
        with open(self.models_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                model_name = row['Large Language Model'].strip()
                if model_name:
                    self.models.append(model_name)
        print(f"Loaded {len(self.models)} models: {self.models}")

    def load_prompts(self):
        """Load the prompt list from prompts.csv"""
        print("Loading prompts from CSV...")
        with open(self.prompts_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = row['Topic'].strip()
                prompt = row['Prompt'].strip()
                if topic and prompt:
                    self.prompts.append({
                        'topic': topic,
                        'prompt': prompt
                    })
        print(f"Loaded {len(self.prompts)} prompts")

    def load_ground_truth(self):
        """Load ground truth and max_depth information from ground_truth.csv"""
        if not self.ground_truth_csv:
            print("No ground truth file provided, skipping...")
            return

        if not os.path.exists(self.ground_truth_csv):
            print(f"Ground truth file not found: {self.ground_truth_csv}")
            return

        print("Loading ground truth from CSV...")
        with open(self.ground_truth_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                problem_name = row['Problem Name'].strip()
                ground_truth = row['Ground-truth'].strip()
                max_depth = row['Max Depth'].strip()

                if problem_name:
                    self.ground_truth_map[problem_name] = ground_truth
                    self.max_depth_map[problem_name] = max_depth

        print(f"Loaded ground truth for {len(self.ground_truth_map)} problems")

    def get_base_problem_name(self, prompt_title: str) -> str:
        """
        Extract the base problem name from a prompt title.
        Example: "Counting sheep. M1" -> "Counting sheep."
        """
        # Remove trailing " M1", " M2", " M3", etc.
        base_name = re.sub(r'\s+M\d+$', '', prompt_title).strip()

        # Ensure it ends with a dot if the original title had one
        if not base_name.endswith('.') and prompt_title.find('.') != -1:
            dot_pos = prompt_title.find('.')
            if dot_pos != -1:
                base_name = prompt_title[:dot_pos + 1]

        return base_name

    def extract_java_code(self, llm_output: str) -> str:
        """
        Extract Java code from LLM output.
        Supports multiple code block formats.
        """
        # Try ```java``` code block
        java_pattern = r'```java\s*(.*?)\s*```'
        matches = re.findall(java_pattern, llm_output, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()

        # Try generic ``` ``` code block
        general_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(general_pattern, llm_output, re.DOTALL)
        if matches:
            # Check for Java-like features
            for match in matches:
                if 'public class' in match or 'class ' in match or 'public static void main' in match:
                    return match.strip()

        # If no code block markers, try to locate Java code by common signatures
        if 'public class' in llm_output or 'public static void main' in llm_output:
            lines = llm_output.split('\n')
            start_idx = -1
            end_idx = -1

            for i, line in enumerate(lines):
                stripped = line.strip()
                if start_idx == -1 and (stripped.startswith('import ') or
                                       stripped.startswith('public class ') or
                                       stripped.startswith('class ')):
                    start_idx = i
                if stripped == '}':
                    end_idx = i

            if start_idx != -1 and end_idx != -1:
                return '\n'.join(lines[start_idx:end_idx + 1]).strip()

        # If everything fails, return the raw output (trimmed)
        return llm_output.strip()

    def call_ollama(self, model: str, prompt: str) -> str:
        """
        Call Ollama to generate code.
        """
        try:
            cmd = ['ollama', 'run', model]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=prompt, timeout=300)

            if process.returncode != 0:
                print(f"Error calling ollama for model {model}: {stderr}")
                return ""

            return stdout.strip()

        except subprocess.TimeoutExpired:
            print(f"Timeout when calling ollama for model {model}")
            process.kill()
            return ""
        except Exception as e:
            print(f"Exception when calling ollama for model {model}: {str(e)}")
            return ""

    def check_existing_output(self, model: str, topic: str) -> Dict[str, Any] | None:
        """
        Check whether generated output already exists.
        If it exists and has 3 versions, skip it.
        """
        model_dir = os.path.join(self.output_base_dir, model)
        output_file = os.path.join(model_dir, "generated_code.json")

        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for item in data:
                    if item.get('prompt_title') == topic:
                        if len(item.get('code_list', [])) >= 3:
                            print(f"Skipping {model} - {topic}: already has 3 versions")
                            return item
                        else:
                            print(f"Found partial data for {model} - {topic}: {len(item.get('code_list', []))} versions")
                            return item
            except Exception as e:
                print(f"Error reading existing file {output_file}: {str(e)}")

        return None

    def save_output(self, model: str, data: List[Dict[str, Any]]):
        """
        Save generated code to a JSON file.
        """
        model_dir = os.path.join(self.output_base_dir, model)
        os.makedirs(model_dir, exist_ok=True)

        output_file = os.path.join(model_dir, "generated_code.json")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Saved output to {output_file}")

    def generate_code_for_model(self, model: str):
        """
        Generate code for all prompts for a given model.
        """
        print(f"\n{'=' * 60}")
        print(f"Processing model: {model}")
        print(f"{'=' * 60}")

        model_dir = os.path.join(self.output_base_dir, model)
        output_file = os.path.join(model_dir, "generated_code.json")

        # Load existing data (if any)
        existing_data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                print(f"Error loading existing data: {str(e)}")

        # Build a map from topic to data item
        data_map = {item['prompt_title']: item for item in existing_data}

        for prompt_info in self.prompts:
            topic = prompt_info['topic']
            prompt = prompt_info['prompt']

            print(f"\nProcessing prompt: {topic}")

            # Check if it already exists
            if topic in data_map:
                existing_item = data_map[topic]
                existing_count = len(existing_item.get('code_list', []))
                if existing_count >= 3:
                    print(f"  Skipping - already has 3 versions")
                    continue
                else:
                    print(f"  Continuing from {existing_count} existing versions")
                    data_item = existing_item
            else:
                # Get base problem name and ground truth
                base_problem_name = self.get_base_problem_name(topic)
                ground_truth = self.ground_truth_map.get(base_problem_name, "")
                max_depth = self.max_depth_map.get(base_problem_name, "")

                # Create a new data item
                data_item = {
                    "prompt_title": topic,
                    "prompt_content": prompt,
                    "code_list": [],
                    "graded_list": [],
                    "ground_truth": ground_truth,
                    "max_depth": max_depth,
                    "jpf_details": [],
                    "jpf_result": [],
                    "codebleu_score": [],
                    "llm_output": [],
                    "pass@1": 0.0,
                    "pass@3": 0.0
                }
                data_map[topic] = data_item

            # Generate 3 versions
            current_count = len(data_item['code_list'])
            for version in range(current_count, 3):
                print(f"  Generating version {version + 1}/3...")

                llm_output = self.call_ollama(model, prompt)

                if not llm_output:
                    print(f"  Warning: Empty output for version {version + 1}")
                    llm_output = "// Error: Failed to generate code"

                extracted_code = self.extract_java_code(llm_output)

                data_item['code_list'].append(extracted_code)
                data_item['llm_output'].append(llm_output)
                data_item['graded_list'].append(False)
                data_item['jpf_details'].append("")
                data_item['jpf_result'].append("")
                data_item['codebleu_score'].append(0.0)

                print(f"  Version {version + 1} generated successfully")

        final_data = list(data_map.values())
        self.save_output(model, final_data)

    def run(self):
        """
        Main entry point.
        """
        print("Starting Ollama Code Generator...")

        self.load_models()
        self.load_prompts()
        self.load_ground_truth()

        for model in self.models:
            try:
                self.generate_code_for_model(model)
            except Exception as e:
                print(f"Error processing model {model}: {str(e)}")
                continue

        print("\n" + "=" * 60)
        print("Code generation completed!")
        print(f"Output directory: {self.output_base_dir}")
        print("=" * 60)


def main():
    import sys
    import os

    # Default file paths (relative to current directory)
    prompts_csv = "prompts.csv"
    models_csv = "models.csv"
    ground_truth_csv = "ground_truth.csv"

    # Allow overriding via CLI args
    if len(sys.argv) > 1:
        prompts_csv = sys.argv[1]
    if len(sys.argv) > 2:
        models_csv = sys.argv[2]
    if len(sys.argv) > 3:
        ground_truth_csv = sys.argv[3]

    # Validate file existence
    if not os.path.exists(prompts_csv):
        print(f"Error: Prompts file not found: {prompts_csv}")
        print("\nUsage:")
        print("  python3 ollama_code_generator.py [prompts.csv] [models.csv] [ground_truth.csv]")
        print("\nOr place the CSV files in the current directory with these names:")
        print("  - prompts.csv")
        print("  - models.csv")
        print("  - ground_truth.csv")
        sys.exit(1)

    if not os.path.exists(models_csv):
        print(f"Error: Models file not found: {models_csv}")
        sys.exit(1)

    if not os.path.exists(ground_truth_csv):
        print(f"Warning: Ground truth file not found: {ground_truth_csv}")
        print("Continuing without ground truth data...")
        ground_truth_csv = None

    print("Using files:")
    print(f"  Prompts: {prompts_csv}")
    print(f"  Models: {models_csv}")
    print(f"  Ground Truth: {ground_truth_csv if ground_truth_csv else 'None'}")
    print()

    generator = OllamaCodeGenerator(prompts_csv, models_csv, ground_truth_csv)
    generator.run()


if __name__ == "__main__":
    main()
