import csv
import re
from collections import defaultdict

csv.field_size_limit(10 * 1024 * 1024)

# 存储每个模型的统计数据
results = defaultdict(lambda: {
    'compilation_errors': 0,
    'jpf_errors': 0,
    'passes': 0,
    'codebleu_sum': 0.0,
    'codebleu_count': 0
})

# 定义 Result 优先级
priority_levels = {
    1: {"success", "Success"},
    2: {"Concurrency bug", "No entry point", "NPE", "Single Thread", "Race Condition"},
    3: {"Compilation failed"}
}

input_file = "finalresult Pass@3 22 llms.csv"
output_file = "Conclusion_pass@3.csv"

# 打开 CSV 并标准化列名
with open(input_file, 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    raw_headers = next(reader)
    headers = [h.strip() for h in raw_headers]

    # 统一大小写，方便匹配
    header_lower = [h.lower() for h in headers]

    # 列名映射：把输入文件列名统一成内部使用的名字
    rename_map = {
        "large language model": "model",
        "problem name": "problem name",
        "result": "result",
        "codebleu": "codebleu"
    }

    header_map = {}
    for i, h in enumerate(header_lower):
        if h in rename_map:
            header_map[rename_map[h]] = i

    required_cols = ["model", "problem name", "result", "codebleu"]
    missing = [col for col in required_cols if col not in header_map]
    if missing:
        raise ValueError(f"❌ 缺少必要列: {missing}\nCSV 实际列名: {headers}")

    model_idx = header_map["model"]
    problem_idx = header_map["problem name"]
    result_idx = header_map["result"]
    codebleu_idx = header_map["codebleu"]

    # 按模型和基础 problem_name 分组
    problem_versions = defaultdict(lambda: defaultdict(list))
    for row in reader:
        if len(row) <= result_idx:
            continue
        model = row[model_idx].strip()
        problem_raw = row[problem_idx].strip()
        base_problem = re.sub(r'V\d+$', '', problem_raw)  # 去掉版本号 Vx
        problem_versions[model][base_problem].append(row)

# 按优先级选择结果
for model, problems in problem_versions.items():
    for base_problem, rows in problems.items():
        selected_row = None
        for level in (1, 2, 3):
            for row in rows:
                if row[result_idx].strip() in priority_levels[level]:
                    selected_row = row
                    break
            if selected_row:
                break

        if not selected_row:
            continue

        result = selected_row[result_idx].strip()
        if result in priority_levels[1]:
            results[model]['passes'] += 1
            try:
                results[model]['codebleu_sum'] += float(selected_row[codebleu_idx])
                results[model]['codebleu_count'] += 1
            except (ValueError, TypeError):
                pass
        elif result in priority_levels[2]:
            results[model]['jpf_errors'] += 1
        elif result in priority_levels[3]:
            results[model]['compilation_errors'] += 1

# 写入结果到 Conclusion_pass@3.csv
with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.writer(outfile)
    writer.writerow([
        'Large Language Model',  # 保持和输入文件一致
        'Compilation Errors',
        'JPF Errors',
        'Passes',
        'Passing Rate',
        'CodeBLEU'
    ])

    for model, data in results.items():
        total = data['compilation_errors'] + data['jpf_errors'] + data['passes']
        if total > 0:
            passing_rate = f"{data['passes']}/{total}({data['passes']/total:.2%})"
        else:
            passing_rate = "0/0(0.00%)"

        codebleu_avg = (
            f"{data['codebleu_sum'] / data['codebleu_count']:.6f}"
            if data['codebleu_count'] > 0 else "N/A"
        )

        writer.writerow([
            model,
            data['compilation_errors'],
            data['jpf_errors'],
            data['passes'],
            passing_rate,
            codebleu_avg
        ])
