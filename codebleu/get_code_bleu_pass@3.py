import csv
import sys
import re
from codebleu import calc_codebleu

# 设置字段大小限制为最大值
csv.field_size_limit(sys.maxsize)

# Step 1: 读取 ground-truth.csv，建立 {problem_name: (reference_code, num_threads)}
ground_truth = {}
with open('ground-truth.csv', 'r', encoding='utf-8') as gt_file:
    reader = csv.reader(gt_file)
    for row in reader:
        if len(row) >= 3:
            problem_name = row[0]
            reference_code = row[1]
            num_threads = row[2]
            ground_truth[problem_name] = (reference_code, num_threads)
        elif len(row) >= 2:
            ground_truth[row[0]] = (row[1], "N/A")  # 线程数缺失时填 "N/A"

# Step 2: 读取 finalresult.csv，准备处理
updated_rows = []
with open('finalresult Pass@3 22 llms.csv', 'r', encoding='utf-8') as final_file:
    reader = csv.reader(final_file)
    header = next(reader)

    # 添加新列标题（如果还未添加）
    if "ground-truth threads" not in header:
        header.append("ground-truth threads")
    if "Syntax Match" not in header:
        header.append("Syntax Match")
    if "Dataflow Match" not in header:
        header.append("Dataflow Match")
    if "CodeBLEU" not in header:
        header.append("CodeBLEU")

    updated_rows.append(header)

    # Step 3: 逐行处理
    for row in reader:
        if len(row) < 5:
            updated_rows.append(row)
            continue

        problem_name_raw = row[1]

        # 去掉版本号后缀 VX，例如 problem1V2 -> problem1
        problem_name = re.sub(r'V\d+$', '', problem_name_raw)

        prediction = row[4]
        gt_entry = ground_truth.get(problem_name)

        if gt_entry:
            reference_code, num_threads = gt_entry

            result = calc_codebleu(
                [reference_code], [prediction],
                lang="java", weights=(0, 0, 0.5, 0.5), tokenizer=None
            )
            # 提取三个分数
            syntax_score = result.get('syntax_match_score', 'N/A')
            dataflow_score = result.get('dataflow_match_score', 'N/A')
            codebleu_score = result.get('codebleu', 'N/A')

            row.append(num_threads)
            row.append(str(syntax_score))
            row.append(str(dataflow_score))
            row.append(str(codebleu_score))
        else:
            row.append("No thread info")
            row.append("N/A")  # syntax_match
            row.append("N/A")  # dataflow_match
            row.append("No reference found")

        updated_rows.append(row)

# Step 4: 写回 finalresult.csv
with open('finalresult Pass@3 22 llms.csv', 'w', encoding='utf-8', newline='') as out_file:
    writer = csv.writer(out_file)
    writer.writerows(updated_rows)

print("处理完成。")
