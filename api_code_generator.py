#!/usr/bin/env python3
"""
API Code Generator (GPT-4, GPT-5, Claude 4.1)
Read models and prompts from CSV files, call APIs to generate Java code, and save as JSON.

Features:
1. Supports GPT-4, GPT-5, and Claude 4.1
2. Saves each generated version immediately to JSON (real-time save)
3. Supports resume from interruption
4. Detailed progress output
5. Atomic write to prevent file corruption
6. Insufficient balance detection for APIs – auto stop with warning
"""

import csv
import json
import os
import re
import time
from typing import List, Dict, Any
from openai import OpenAI
import anthropic


class InsufficientFundsError(Exception):
    """Exception raised when API balance is insufficient."""
    pass


class APICodeGenerator:
    def __init__(self, prompts_csv: str, ground_truth_csv: str = None,
                 output_base_dir: str = None):
        self.prompts_csv = prompts_csv
        self.ground_truth_csv = ground_truth_csv

        if output_base_dir is None:
            script_dir = os.getcwd()
            self.output_base_dir = os.path.join(script_dir, "Generated_Code")
        else:
            self.output_base_dir = output_base_dir

        self.openai_api_key = "YOUR_OPENAI_API_KEY"
        self.anthropic_api_key = "YOUR_ANTHROPIC_API_KEY"

        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)

        self.models = {
            "gpt-4o": {"type": "openai", "name": "gpt-4o"},
            "gpt-5": {"type": "openai", "name": "gpt-5"},
            "claude-opus-4-1-20250805": {"type": "anthropic", "name": "claude-opus-4-1-20250805"}
        }

        self.prompts = []
        self.ground_truth_map = {}
        self.max_depth_map = {}

    def load_prompts(self):
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
        base_name = re.sub(r'\s+M\d+$', '', prompt_title).strip()
        if not base_name.endswith('.') and prompt_title.find('.') != -1:
            dot_pos = prompt_title.find('.')
            if dot_pos != -1:
                base_name = prompt_title[:dot_pos + 1]
        return base_name

    def extract_java_code(self, llm_output: str) -> str:
        java_pattern = r'```java\s*(.*?)\s*```'
        matches = re.findall(java_pattern, llm_output, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()

        general_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(general_pattern, llm_output, re.DOTALL)
        if matches:
            for match in matches:
                if 'public class' in match or 'class ' in match or 'public static void main' in match:
                    return match.strip()

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

        return llm_output.strip()

    def call_openai(self, model: str, prompt: str) -> str:
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in [
                'insufficient_quota', 'quota', 'billing', 'payment',
                'rate_limit', 'credit', 'balance', 'exceeded'
            ]):
                print("OpenAI API balance insufficient or quota exceeded.")
                print(f"Error: {e}")
                print("Please recharge your OpenAI account:")
                print("https://platform.openai.com/account/billing")
                print("After recharging, restart the script to resume.")
                raise InsufficientFundsError(f"OpenAI insufficient balance: {e}")
            else:
                print(f"Error calling OpenAI ({model}): {str(e)}")
                return ""

    def call_anthropic(self, model: str, prompt: str) -> str:
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in [
                'insufficient_quota', 'quota', 'billing', 'payment',
                'rate_limit', 'credit', 'balance', 'exceeded', 'limit'
            ]):
                print("Anthropic API balance insufficient or quota exceeded.")
                print(f"Error: {e}")
                print("Please recharge your Anthropic account:")
                print("https://console.anthropic.com/settings/billing")
                print("After recharging, restart the script to resume.")
                raise InsufficientFundsError(f"Anthropic insufficient balance: {e}")
            else:
                print(f"Error calling Anthropic API ({model}): {str(e)}")
                return ""

    def call_llm(self, model_key: str, prompt: str) -> str:
        model_info = self.models[model_key]

        if model_info["type"] == "openai":
            return self.call_openai(model_info["name"], prompt)
        elif model_info["type"] == "anthropic":
            return self.call_anthropic(model_info["name"], prompt)
        else:
            print(f"Unknown model type: {model_info['type']}")
            return ""

    def load_existing_data(self, output_file: str) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(output_file):
            return {}

        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

            data_map = {item['prompt_title']: item for item in existing_data}
            print(f"Loaded {len(data_map)} existing prompts from file")
            return data_map

        except Exception as e:
            print(f"Error loading existing data: {str(e)}")
            return {}

    def save_data_immediately(self, output_file: str, data_map: Dict[str, Dict[str, Any]]):
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            final_data = list(data_map.values())

            temp_file = output_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=4, ensure_ascii=False)

            os.replace(temp_file, output_file)

            return True
        except Exception as e:
            print(f"Error saving data: {str(e)}")
            return False

    def create_or_get_data_item(self, topic: str, prompt: str, data_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        if topic in data_map:
            return data_map[topic]

        base_problem_name = self.get_base_problem_name(topic)
        ground_truth = self.ground_truth_map.get(base_problem_name, "")
        max_depth = self.max_depth_map.get(base_problem_name, "")

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
        return data_item

    def generate_code_for_model(self, model_key: str):
        print("Processing model:", model_key)

        model_dir = os.path.join(self.output_base_dir, model_key)
        output_file = os.path.join(model_dir, "generated_code.json")

        data_map = self.load_existing_data(output_file)

        total_to_generate = 0
        already_complete = 0

        for prompt_info in self.prompts:
            topic = prompt_info['topic']
            if topic in data_map:
                existing_count = len(data_map[topic].get('code_list', []))
                if existing_count >= 3:
                    already_complete += 1
                else:
                    total_to_generate += (3 - existing_count)
            else:
                total_to_generate += 3

        print("Total prompts:", len(self.prompts))
        print("Already complete:", already_complete)
        print("Versions to generate:", total_to_generate)

        if total_to_generate == 0:
            print("All prompts already have 3 versions.")
            return

        generated_count = 0

        for prompt_idx, prompt_info in enumerate(self.prompts, 1):
            topic = prompt_info['topic']
            prompt = prompt_info['prompt']

            print(f"Processing ({prompt_idx}/{len(self.prompts)}): {topic}")

            data_item = self.create_or_get_data_item(topic, prompt, data_map)

            current_count = len(data_item['code_list'])

            if current_count >= 3:
                print("Already has 3 versions, skipping")
                continue

            print(f"Current versions: {current_count}/3")

            for version in range(current_count, 3):
                version_num = version + 1
                print(f"Generating version {version_num}...", end=" ", flush=True)

                start_time = time.time()

                try:
                    llm_output = self.call_llm(model_key, prompt)
                except InsufficientFundsError:
                    print("Insufficient balance detected, saving progress...")
                    self.save_data_immediately(output_file, data_map)
                    print("Progress saved.")
                    raise

                generation_time = time.time() - start_time

                if not llm_output:
                    print(f"Empty output ({generation_time:.1f}s)")
                    llm_output = "// Error: Failed to generate code"
                else:
                    print(f"Done ({generation_time:.1f}s)")

                extracted_code = self.extract_java_code(llm_output)

                data_item['code_list'].append(extracted_code)
                data_item['llm_output'].append(llm_output)
                data_item['graded_list'].append(False)
                data_item['jpf_details'].append("")
                data_item['jpf_result'].append("")
                data_item['codebleu_score'].append(0.0)

                print("Saving...", end=" ", flush=True)
                if self.save_data_immediately(output_file, data_map):
                    print("Saved")
                    generated_count += 1
                else:
                    print("Save failed")

                print(f"Progress: {generated_count}/{total_to_generate}")

        print("Final save for model:", model_key)
        if self.save_data_immediately(output_file, data_map):
            print("Successfully saved.")
            print("Generated versions:", generated_count)
        else:
            print("Final save error.")

    def run(self):
        print("API Code Generator")
        print("Output directory:", self.output_base_dir)

        self.load_prompts()
        self.load_ground_truth()

        for model_idx, model_key in enumerate(self.models.keys(), 1):
            print(f"Model {model_idx}/{len(self.models)}: {model_key}")

            try:
                self.generate_code_for_model(model_key)
            except InsufficientFundsError as e:
                print("Program terminated due to insufficient API balance.")
                print("Reason:", str(e))
                print("Progress saved. After recharging, restart to resume.")
                return
            except KeyboardInterrupt:
                print("Interrupted by user. Progress saved.")
                return
            except Exception as e:
                print(f"Error processing model {model_key}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print("Code generation completed.")
        print("Output directory:", self.output_base_dir)


def main():
    import sys

    default_prompts = "prompts.csv"
    default_ground_truth = "ground_truth.csv"

    prompts_csv = default_prompts
    ground_truth_csv = default_ground_truth

    if len(sys.argv) > 1:
        prompts_csv = sys.argv[1]
    if len(sys.argv) > 2:
        ground_truth_csv = sys.argv[2]

    if not os.path.exists(prompts_csv):
        print(f"Error: Prompts file not found: {prompts_csv}")
        print("Usage: python3 api_code_generator.py [prompts.csv] [ground_truth.csv]")
        sys.exit(1)

    if not os.path.exists(ground_truth_csv):
        print(f"Warning: Ground truth file not found: {ground_truth_csv}")
        print("Continuing without ground truth data...")
        ground_truth_csv = None

    print("Using files:")
    print("  Prompts:", prompts_csv)
    print("  Ground Truth:", ground_truth_csv if ground_truth_csv else "None")
    print()

    generator = APICodeGenerator(prompts_csv, ground_truth_csv)

    try:
        generator.run()
    except InsufficientFundsError:
        print("Script terminated due to insufficient API balance. Progress saved.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Program interrupted by user. Progress saved.")


if __name__ == "__main__":
    main()
