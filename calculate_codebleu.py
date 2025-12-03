#!/usr/bin/env python3

import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

try:
    from codebleu import calc_codebleu
except ImportError:
    print("Error: codebleu library not found.")
    print("Install with: pip install codebleu --break-system-packages")
    sys.exit(1)


class CodeBLEUCalculatorV2:
    def __init__(self, ground_truth_csv: str, generated_code_dir: str = None):
        self.ground_truth_csv = ground_truth_csv

        if generated_code_dir is None:
            script_dir = os.getcwd()
            self.generated_code_dir = os.path.join(script_dir, "Generated_Code")
        else:
            self.generated_code_dir = generated_code_dir

        self.ground_truth_map = {}

    def load_ground_truth(self):
        print(f"Loading ground truth from: {self.ground_truth_csv}")

        if not os.path.exists(self.ground_truth_csv):
            print(f"Error: Ground truth file not found: {self.ground_truth_csv}")
            sys.exit(1)

        with open(self.ground_truth_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                problem_name = row['Problem Name'].strip()
                ground_truth = row['Ground-truth'].strip()

                if problem_name and ground_truth:
                    self.ground_truth_map[problem_name] = ground_truth

        print(f"Loaded {len(self.ground_truth_map)} ground truth codes")
        print()

    def get_base_problem_name(self, prompt_title: str) -> str:
        base_name = re.sub(r'\s+M\d+$', '', prompt_title).strip()
        if not base_name.endswith('.') and prompt_title.find('.') != -1:
            dot_pos = prompt_title.find('.')
            if dot_pos != -1:
                base_name = prompt_title[:dot_pos + 1]
        return base_name

    def calculate_codebleu(self, generated_code: str, ground_truth: str) -> float:
        if not ground_truth or not generated_code:
            return 0.0

        try:
            result = calc_codebleu(
                references=[ground_truth],
                predictions=[generated_code],
                lang="java",
                weights=(0.0, 0.0, 0.5, 0.5),
                tokenizer=None
            )

            syntax_score = result.get('syntax_match_score', 0.0)
            dataflow_score = result.get('dataflow_match_score', 0.0)

            avg_score = (syntax_score + dataflow_score) / 2.0
            codebleu_score = avg_score * 100

            return round(codebleu_score, 2)

        except Exception as e:
            print(f"Error calculating CodeBLEU: {str(e)}")
            return 0.0

    def process_model_json(self, model_name: str, json_path: str):
        print(f"Processing: {model_name}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        updated_count = 0
        total_codes = 0

        for item in data:
            prompt_title = item['prompt_title']
            base_name = self.get_base_problem_name(prompt_title)

            ground_truth = self.ground_truth_map.get(base_name, "")

            if not item.get('ground_truth'):
                item['ground_truth'] = ground_truth

            code_list = item.get('code_list', [])
            codebleu_scores = []

            for i, code in enumerate(code_list):
                existing_scores = item.get('codebleu_score', [])
                if i < len(existing_scores) and existing_scores[i] > 0:
                    score = existing_scores[i]
                    print(f"  {prompt_title} - Version {i + 1}: Using existing score {score:.2f}")
                else:
                    score = self.calculate_codebleu(code, ground_truth)
                    print(f"  {prompt_title} - Version {i + 1}: Calculated score {score:.2f}")
                    updated_count += 1

                codebleu_scores.append(score)
                total_codes += 1

            item['codebleu_score'] = codebleu_scores

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"  Updated {updated_count}/{total_codes} code scores")

        if total_codes > 0:
            all_scores = [score for item in data for score in item.get('codebleu_score', []) if score > 0]
            if all_scores:
                avg_score = sum(all_scores) / len(all_scores)
                print(f"  Average CodeBLEU: {avg_score:.2f}")

        print()

        return updated_count, total_codes

    def process_all_models(self):
        if not os.path.exists(self.generated_code_dir):
            print(f"Error: Generated code directory not found: {self.generated_code_dir}")
            sys.exit(1)

        model_dirs = [d for d in os.listdir(self.generated_code_dir)
                      if os.path.isdir(os.path.join(self.generated_code_dir, d))]

        if not model_dirs:
            print(f"No model directories found in: {self.generated_code_dir}")
            sys.exit(1)

        print(f"Found {len(model_dirs)} model directories")
        print()

        total_updated = 0
        total_codes = 0

        for model_name in sorted(model_dirs):
            json_path = os.path.join(self.generated_code_dir, model_name, "generated_code.json")

            if not os.path.exists(json_path):
                print(f"Skipping {model_name}: JSON file not found")
                continue

            updated, codes = self.process_model_json(model_name, json_path)
            total_updated += updated
            total_codes += codes

        print("======================================================================")
        print(f"Completed. Updated {total_updated}/{total_codes} CodeBLEU scores")
        print("======================================================================")

    def generate_summary(self):
        print("Generating summary report...")

        summary = {}

        model_dirs = [d for d in os.listdir(self.generated_code_dir)
                      if os.path.isdir(os.path.join(self.generated_code_dir, d))]

        for model_name in sorted(model_dirs):
            json_path = os.path.join(self.generated_code_dir, model_name, "generated_code.json")

            if not os.path.exists(json_path):
                continue

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            scores = [score for item in data for score in item.get('codebleu_score', []) if score > 0]

            if scores:
                summary[model_name] = {
                    'total_codes': len(scores),
                    'avg_score': round(sum(scores) / len(scores), 2),
                    'min_score': round(min(scores), 2),
                    'max_score': round(max(scores), 2),
                    'scores_above_70': len([s for s in scores if s >= 70]),
                    'scores_above_50': len([s for s in scores if s >= 50]),
                }

        summary_path = os.path.join(self.generated_code_dir, "codebleu_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)

        print(f"Summary saved to: {summary_path}")
        print()

        print("CodeBLEU Summary:")
        print("----------------------------------------------------------------------")
        for model_name, stats in sorted(summary.items()):
            print(f"\n{model_name}:")
            print(f"  Total codes: {stats['total_codes']}")
            print(f"  Average: {stats['avg_score']}")
            print(f"  Range: {stats['min_score']} - {stats['max_score']}")
            print(f"  Good (>=70): {stats['scores_above_70']}")
            print(f"  Acceptable (>=50): {stats['scores_above_50']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Calculate CodeBLEU scores using official library'
    )

    parser.add_argument(
        '-g', '--ground-truth',
        default='ground_truth.csv',
        help='Path to ground_truth.csv file'
    )

    parser.add_argument(
        '-d', '--directory',
        default=None,
        help='Path to Generated_Code directory'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Only generate summary report'
    )

    args = parser.parse_args()

    if not args.summary_only and not os.path.exists(args.ground_truth):
        print(f"Error: Ground truth file not found: {args.ground_truth}")
        print("Ensure ground_truth.csv exists or specify path with -g")
        sys.exit(1)

    calculator = CodeBLEUCalculatorV2(args.ground_truth, args.directory)

    if not os.path.exists(calculator.generated_code_dir):
        print(f"Error: Generated code directory not found: {calculator.generated_code_dir}")
        print("Ensure the directory exists or specify path with -d")
        sys.exit(1)

    if not args.summary_only:
        calculator.load_ground_truth()
        calculator.process_all_models()

    calculator.generate_summary()


if __name__ == "__main__":
    main()
