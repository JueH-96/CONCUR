import os
import re
import pandas as pd
from openai import OpenAI

# ==== Configuration ====
MODEL_NAME = "gpt-5"  # Change to GPT-5
CSV_FILE = "problemlist.csv"
OUTPUT_BASE = "examples"
API_KEY = ""  # Replace with your API Key
client = OpenAI(api_key=API_KEY)

def clean_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name.strip())

def extract_class_name(java_code: str) -> str:
    match = re.search(r'public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)', java_code)
    if match:
        return match.group(1)
    return None

df = pd.read_csv(CSV_FILE)

for idx, row in df.iterrows():
    prompt = row["Prompt"]
    topic = clean_name(str(row["Topic"]))
    tmp_file_name = f"problem_{idx+1}.java"
    save_dir = os.path.join(OUTPUT_BASE, MODEL_NAME, topic)
    os.makedirs(save_dir, exist_ok=True)
    tmp_save_path = os.path.join(save_dir, tmp_file_name)

    if os.path.exists(tmp_save_path):
        print(f"Skipping {tmp_save_path}, already exists.")
        continue

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        code_blocks = re.findall(r"```(?:java)?\n(.*?)```", content, re.DOTALL)
        final_code = code_blocks[0].strip() if code_blocks else content
        class_name = extract_class_name(final_code)
        if not class_name:
            class_name = f"problem_{idx+1}"
        final_file_name = f"{class_name}.java"
        final_save_path = os.path.join(save_dir, final_file_name)

        with open(final_save_path, "w", encoding="utf-8") as f:
            f.write(final_code)

        if os.path.exists(tmp_save_path):
            os.remove(tmp_save_path)

        print(f"Saved: {final_save_path}")

    except Exception as e:
        print(f"Error processing row {idx+1}: {e}")
