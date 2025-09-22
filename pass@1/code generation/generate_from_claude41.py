import os
import re
import pandas as pd
import anthropic

# ==== Configuration ====
MODEL_NAME = "claude-opus-4-1-20250805"  # Claude Opus 4 (latest Claude 4.1)
CSV_FILE = "problemlist.csv"
OUTPUT_BASE = "examples"
API_KEY = ""  # Replace with your Anthropic API Key

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=API_KEY)


def clean_name(name: str) -> str:
    """Clean file name by removing invalid characters"""
    return re.sub(r'[\\/*?:"<>|]', "_", name.strip())


def extract_class_name(java_code: str) -> str:
    """Extract class name from Java code"""
    match = re.search(r'public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)', java_code)
    if match:
        return match.group(1)
    return None


# Load CSV file
df = pd.read_csv(CSV_FILE)

for idx, row in df.iterrows():
    prompt = row["Prompt"]
    topic = clean_name(str(row["Topic"]))
    tmp_file_name = f"problem_{idx + 1}.java"

    # Create output directory
    save_dir = os.path.join(OUTPUT_BASE, MODEL_NAME, topic)
    os.makedirs(save_dir, exist_ok=True)

    tmp_save_path = os.path.join(save_dir, tmp_file_name)

    # Skip existing files
    if os.path.exists(tmp_save_path):
        print(f"Skipping {tmp_save_path}, already exists.")
        continue

    try:
        # Call Claude API
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4000,  # Claude requires max token count
            temperature=0.7,  # Optional: controls creativity
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Get response content
        content = response.content[0].text.strip()

        # Extract code blocks
        code_blocks = re.findall(r"```(?:java)?\n(.*?)```", content, re.DOTALL)
        final_code = code_blocks[0].strip() if code_blocks else content

        # Extract class name
        class_name = extract_class_name(final_code)
        if not class_name:
            class_name = f"Problem_{idx + 1}"

        # Save file
        final_file_name = f"{class_name}.java"
        final_save_path = os.path.join(save_dir, final_file_name)

        with open(final_save_path, "w", encoding="utf-8") as f:
            f.write(final_code)

        # Delete temp file if it exists
        if os.path.exists(tmp_save_path):
            os.remove(tmp_save_path)

        print(f"Saved: {final_save_path}")

    except Exception as e:
        print(f"Error processing row {idx + 1}: {e}")
        continue

print("Processing completed!")
