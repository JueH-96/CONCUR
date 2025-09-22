import csv
import sys
import re
from collections import defaultdict

csv.field_size_limit(10 * 1024 * 1024)

# Save resports
results = defaultdict(lambda: {
    'compilation_errors': 0,
    'jpf_errors': 0,
    'passes': 0,
    'codebleu_sum': 0.0,
    'codebleu_count': 0
})

# Define priority for Result 
priority_levels = {
    1: ["success", "Success", "Pass JPF evaluation"],
    2: ["Concurrency bug", "No entry point", "NPE", "Single Thread"],
    3: ["Compilation failed"]
}

# read original CSV
with open('finalresult.csv', 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader)

    try:
        model_idx = headers.index("Model") if "Model" in headers else 0
        problem_idx = headers.index("problem name") if "problem name" in headers else 1
        result_idx = headers.index("Result") if "Result" in headers else 2
        codebleu_idx = headers.index("CodeBLEU")
    except ValueError as e:
        print(f"Error：cannot match necessary column: {e}")
        sys.exit(1)

    # Divide results by models and problem names
    problem_versions = defaultdict(lambda: defaultdict(list))

    for row in reader:
        if len(row) <= result_idx:
            continue
        model_name = row[model_idx].strip()
        problem_name_raw = row[problem_idx].strip()
        base_problem_name = re.sub(r'V\d+$', '', problem_name_raw)  # remove version number Vx
        problem_versions[model_name][base_problem_name].append(row)

# Order result based on priority
for model, problems in problem_versions.items():
    for base_problem_name, rows in problems.items():
        selected_row = None
        for level in [1, 2, 3]:
            for row in rows:
                result = row[result_idx].strip()
                if result in priority_levels[level]:
                    selected_row = row
                    break
            if selected_row:
                break

        if not selected_row:
            continue

        result = selected_row[result_idx].strip()

        # Update report
        if result in priority_levels[1]:
            results[model]['passes'] += 1
            try:
                codebleu_val = float(selected_row[codebleu_idx])
                results[model]['codebleu_sum'] += codebleu_val
                results[model]['codebleu_count'] += 1
            except ValueError:
                pass
        elif result in priority_levels[2]:
            results[model]['jpf_errors'] += 1
        elif result in priority_levels[3]:
            results[model]['compilation_errors'] += 1

# Write results to Conclusion.csv
with open('Conclusion.csv', 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.writer(outfile)
    writer.writerow([
        'Large Language Models',
        'Compilation Errors',
        'JPF Errors',
        'Passes',
        'Passing Rate',
        'CodeBLEU'
    ])

    for model, data in results.items():
        total = data['compilation_errors'] + data['jpf_errors'] + data['passes']
        if total > 0:
            passing_rate = f"{data['passes'] / total:.2%}"
        else:
            passing_rate = "N/A"

        if data['codebleu_count'] > 0:
            codebleu_avg = f"{data['codebleu_sum'] / data['codebleu_count']:.6f}"
        else:
            codebleu_avg = "N/A"

        writer.writerow([
            model,
            data['compilation_errors'],
            data['jpf_errors'],
            data['passes'],
            passing_rate,
            codebleu_avg
        ])
