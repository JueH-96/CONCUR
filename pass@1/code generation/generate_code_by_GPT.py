import os
import re
import pandas as pd
from openai import OpenAI

# Configuration
MODEL_NAME = "gpt-4o"
CSV_FILE = "problemlist.csv"   # Path to the CSV file
OUTPUT_BASE = "examples"       # Root directory for saving results
API_KEY = ""  # Replace with your API Key
client = OpenAI(api_key=API_KEY)

# Clean directory name (remove invalid characters from Topic)
def clean_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name.strip())

# Read CSV
df = pd.read_csv(CSV_FILE)

# Extract the class name after "public class"
def extract_class_name(java_code: str) -> str:
    # Regex to match class name after "public class", allowing spaces or newlines
    match = re.search(r'public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)', java_code)
    if match:
        return match.group(1)
    return None

# Iterate through each row
for idx, row in df.iterrows():
    prompt = row["Prompt"]
    topic = clean_name(str(row["Topic"]))
    # Temporary file name to avoid conflicts during folder creation
    tmp_file_name = f"problem_{idx+1}.java"

    # Save path: /examples/<model_name>/<Topic>/
    save_dir = os.path.join(OUTPUT_BASE, MODEL_NAME, topic)
    os.makedirs(save_dir, exist_ok=True)
    tmp_save_path = os.path.join(save_dir, tmp_file_name)

    # Skip if temporary file already exists
    if os.path.exists(tmp_save_path):
        print(f"Skipping {tmp_save_path}, already exists.")
        continue

    try:
        # Call the LLM
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        # Prefer extracting ```java code blocks
        code_blocks = re.findall(r"```(?:java)?\n(.*?)```", content, re.DOTALL)

        # If not found, use the entire content
        final_code = code_blocks[0].strip() if code_blocks else content

        # Extract class name
        class_name = extract_class_name(final_code)
        if not class_name:
            # Use default file name if class name not found
            class_name = f"problem_{idx+1}"

        final_file_name = f"{class_name}.java"
        final_save_path = os.path.join(save_dir, final_file_name)

        # Write file
        with open(final_save_path, "w", encoding="utf-8") as f:
            f.write(final_code)

        # Delete temporary file if it exists
        if os.path.exists(tmp_save_path):
            os.remove(tmp_save_path)

        print(f"Saved: {final_save_path}")

    except Exception as e:
        print(f"Error processing row {idx+1}: {e}")
