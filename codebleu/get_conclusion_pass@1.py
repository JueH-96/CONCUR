import csv
import sys
from collections import defaultdict

# set limitation for string length to max
csv.field_size_limit(10 * 1024 * 1024)

# save all models' result
results = defaultdict(lambda: {
    'total_count': 0,
    'codebleu_sum': 0.0,
    'pass_jpf_eval': 0,
    'jpf_eval_fail': 0,
    'compilation_fail': 0
})

# read original CSV
with open('finalresult Pass@1 22 llms.csv', 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader)

    try:
        model_idx = headers.index("Model") if "Model" in headers else 0
        result_idx = headers.index("Result") if "Result" in headers else 2
        codebleu_idx = headers.index("CodeBLEU")
    except ValueError as e:
        print(f"Error：Cannot find necessary column name:{e}")
        sys.exit(1)

    for row in reader:
        if len(row) <= max(result_idx, codebleu_idx):
            continue

        model_name = row[model_idx].strip()
        result = row[result_idx].strip()

        try:
            codebleu = float(row[codebleu_idx])
        except ValueError:
            codebleu = 0.0

        # Update report
        results[model_name]['total_count'] += 1
        results[model_name]['codebleu_sum'] += codebleu

        # Count Compilation Fail（Result Column is "Syntax error"）
        if result == "Syntax error":
            results[model_name]['compilation_fail'] += 1
        # Count Pass JPF Evaluation
        elif result in ["Pass JPF evaluation", "Success", "success", "Passes"]:
            results[model_name]['pass_jpf_eval'] += 1
        # Count JPF Evaluation Fail
        elif result in ["Concurrency bug", "NPE", "Single Thread", "Race Condition", "JPF Errors", "Termination Error"]:
            results[model_name]['jpf_eval_fail'] += 1

# Write result to Conclusion.csv with new column names
with open('Conclusion_pass@1.csv', 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.writer(outfile)

    # New column names
    writer.writerow([
        'Large Language Model',
        'Compilation Errors',
        'JPF Errors',
        'Passes',
        'Passing Rate',
        'CodeBLEU'
    ])

    for model, data in results.items():
        total = data['total_count']
        if total == 0:
            continue

        passing_rate = f"{data['pass_jpf_eval']}/{total} ({data['pass_jpf_eval']/total:.2%})"
        codebleu_avg = data['codebleu_sum'] / total

        writer.writerow([
            model,
            data['compilation_fail'],
            data['jpf_eval_fail'],
            data['pass_jpf_eval'],
            passing_rate,
            f"{codebleu_avg:.6f}"
        ])
