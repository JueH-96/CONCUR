#!/usr/bin/env python3.12
import os
import csv

def main():
    root_dir = os.path.join(os.getcwd(), 'examples')
    output_dir = os.path.join(os.getcwd(), 'jpfevaluation')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'jpf_result_list.csv')

    csv_header = ['large language model', 'problem name', 'concurrency bug']
    results = []

    for llm_name in os.listdir(root_dir):
        llm_path = os.path.join(root_dir, llm_name)
        if not os.path.isdir(llm_path):
            continue

        for problem_name in os.listdir(llm_path):
            problem_path = os.path.join(llm_path, problem_name)
            if not os.path.isdir(problem_path):
                continue

            # Get list of .jpf files; skip this problem if none exist
            jpf_files = [f for f in os.listdir(problem_path) if f.endswith('.jpf')]
            if not jpf_files:
                continue

            # Get list of .txt files; skip if none exist
            txt_files = [f for f in os.listdir(problem_path) if f.endswith('.txt')]
            if not txt_files:
                continue

            for txt_file in txt_files:
                txt_path = os.path.join(problem_path, txt_file)
                try:
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Failed to read file: {txt_path}, Error: {e}")
                    continue

                bug_info = None
                content_lower = content.lower()

                # Priority 1: Single-threaded execution
                if 'unique logical threads created during execution: 1' in content:
                    bug_info = 'unmultithreaded execution'
                # Priority 2: No errors detected or compilation failed -> skip
                elif 'no errors detected' in content_lower or 'compilation failed' in content_lower:
                    continue
                # Results + statistics block
                elif '====================================================== results' in content and '====================================================== statistics' in content:
                    start_index = content.index('====================================================== results') + len('====================================================== results')
                    end_index = content.index('====================================================== statistics')
                    bug_info = content[start_index:end_index].strip()
                # NullPointerException without results
                elif 'nullpointerexception' in content_lower and '====================================================== results' not in content:
                    bug_info = 'NPE'
                # [SEVERE] message at the start
                elif content.lstrip().startswith('[SEVERE]'):
                    bug_info = content.strip()
                # Out of memory
                elif 'ut of memor' in content_lower:
                    bug_info = 'out of memory'
                # Fallback
                else:
                    bug_info = 'state space / path explosion'

                results.append([llm_name, problem_name, bug_info])

    # Write results to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_header)
        writer.writerows(results)

    print(f'Processing complete. Results saved to {output_file}')


if __name__ == '__main__':
    main()
