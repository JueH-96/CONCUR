import csv
import sys
from collections import defaultdict

csv.field_size_limit(10 * 1024 * 1024)

results = defaultdict(lambda: {
    'total_count': 0,
    'codebleu_sum': 0.0,
    'pass_jpf_eval': 0,
    'jpf_eval_fail': 0,
    'compilation_fail': 0,
    'codebleu_count': 0  
})

with open('finalresult.csv', 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader)

    try:
        model_idx = headers.index("Model") if "Model" in headers else 0
        result_idx = headers.index("Result") if "Result" in headers else 2
        codebleu_idx = headers.index("CodeBLEU")
    except ValueError as e:
        print(f"Error：cannot find necessory column:，message:{e}")
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

        results[model_name]['total_count'] += 1

        # Count Compilation Fail
        if result == "Syntax error":
            results[model_name]['compilation_fail'] += 1
        # Count Pass JPF Evaluation
        elif result in ["Pass JPF evaluation", "Success", "success"]:
            results[model_name]['pass_jpf_eval'] += 1
            # Only calcualte passing codes CodeBLEU
            results[model_name]['codebleu_sum'] += codebleu
            results[model_name]['codebleu_count'] += 1
        # Count JPF Evaluation Fail
        elif result in ["Concurrency bug", "NPE", "Single Thread"]:
            results[model_name]['jpf_eval_fail'] += 1

# Save result
with open('Conclusion.csv', 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.writer(outfile)
    writer.writerow([
        'Large Language Model',
        'Compilation Fail',
        'JPF Evaluation Fail',
        'Pass JPF Evaluation',
        'Passing Rate',
        'CodeBLEU'
    ])

    for model, data in results.items():
        total = data['total_count']
        if total == 0:
            continue

        passing_rate = f"{data['pass_jpf_eval']}/{total} ({data['pass_jpf_eval']/total:.2%})"
        # Use codebleu_count to get avg
        codebleu_avg = data['codebleu_sum'] / data['codebleu_count'] if data['codebleu_count'] > 0 else 0.0

        writer.writerow([
            model,
            data['compilation_fail'],
            data['jpf_eval_fail'],
            data['pass_jpf_eval'],
            passing_rate,
            f"{codebleu_avg:.6f}"
        ])
