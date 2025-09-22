#!/bin/bash

set -x

# ----------------------------
# Helper function to write result to CSV
write_result_to_csv() {
    if [ ! -f "$RESULT_CSV" ]; then
        echo "Seq,Topic,Model Name,Result" > "$RESULT_CSV"
    fi

    # Find current max sequence number
    MAX_SEQ=0
    while IFS=, read -r seq _ _ _; do
        if [[ "$seq" =~ ^[0-9]+$ ]]; then
            MAX_SEQ=$((MAX_SEQ < seq ? seq : MAX_SEQ))
        fi
    done < "$RESULT_CSV"

    NEW_SEQ=$((MAX_SEQ + 1))

    # Append new record
    echo "$NEW_SEQ,$CUSTOM_FOLDER_NAME,$MODEL_NAME,\"$STATUS\"" >> "$RESULT_CSV"

    echo "Result appended to: $RESULT_CSV"
}

# ----------------------------
# Main script starts here

if [ $# -lt 3 ]; then
    echo "Usage: ./generate_java.sh <custom_folder_name> <model_name> \"<prompt>\""
    exit 1
fi

CUSTOM_FOLDER_NAME="$1"
MODEL_NAME="$2"
PROMPT="$3"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="examples/${MODEL_NAME}/${CUSTOM_FOLDER_NAME}"
mkdir -p "$SCRIPT_DIR/$OUTPUT_DIR"
echo "Ensured directory exists: $SCRIPT_DIR/$OUTPUT_DIR"

RESULT_CSV="$SCRIPT_DIR/result.csv"
LOG_CSV="$SCRIPT_DIR/generatedLog.csv"

# ----------------------------
# Check if Java file already exists
if compgen -G "$SCRIPT_DIR/$OUTPUT_DIR/*.java" > /dev/null; then
    echo "Java file already exists in $OUTPUT_DIR. Skipping generation."
    STATUS="skipped_existing_file"
    write_result_to_csv
    exit 0
fi

# Write the full prompt to a temporary file using printf to preserve line breaks and special characters
TMP_PROMPT="/tmp/prompt_$$"
{
    printf '%s' "$PROMPT"
} > "$TMP_PROMPT"

# ----------------------------
# Try to extract Java code block up to 50 times
MAX_RETRIES=50
RETRY_COUNT=0
CODE_BLOCK=""

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Attempt $RETRY_COUNT to get Java code..."

    RESPONSE=$(cat "$TMP_PROMPT" | ollama run "$MODEL_NAME")

    CODE_BLOCK=$(echo "$RESPONSE" | sed -n '/```java$/,/```$/ { /```java$/d; /```$/d; p }')

    if [ ! -z "$CODE_BLOCK" ]; then
        break
    else
        echo "No Java code block found. Retrying..."
    fi
done

rm -f "$TMP_PROMPT"

# ----------------------------
# Handle failure
if [ -z "$CODE_BLOCK" ]; then
    echo "Failed to generate valid Java code after $MAX_RETRIES attempts."

    # Write to generatedLog.csv
    if [ ! -f "$LOG_CSV" ]; then
        echo "Large Language Model,Prompt,Generated result,Attempt count" > "$LOG_CSV"
    fi

    ESCAPED_PROMPT=$(echo "$PROMPT" | sed 's/"/""/g')
    echo "\"$MODEL_NAME\",\"$ESCAPED_PROMPT\",failed,$RETRY_COUNT" >> "$LOG_CSV"
    echo "Failure logged to: $LOG_CSV"

    # Write full response to a .txt file
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    ERROR_FILENAME="FailedGeneration_${TIMESTAMP}.txt"
    TXT_FILE_PATH="$SCRIPT_DIR/$OUTPUT_DIR/$ERROR_FILENAME"

    {
        echo "Generation failed after $MAX_RETRIES attempts"
        echo "Timestamp: $TIMESTAMP"
        echo "Prompt:"
        echo "$PROMPT"
        echo
        echo "Last ollama response:"
        echo "$RESPONSE"
    } > "$TXT_FILE_PATH"

    echo "Failure info written to: $TXT_FILE_PATH"

    STATUS="generation code failed"
    write_result_to_csv
    exit 1
fi

# ----------------------------
# Extract public class name
CLASS_NAME=$(echo "$CODE_BLOCK" | grep -oP 'public\s+class\s+\K\w+' | head -n1)
CLASS_NAME=${CLASS_NAME:-$(echo "$CODE_BLOCK" | grep -Eo 'class\s+[a-zA-Z_][a-zA-Z0-9_]*' | head -n1 | awk '{print $2}')}

if [ -z "$CLASS_NAME" ]; then
    echo "No class definition found."
    STATUS="no class found"
    write_result_to_csv
    exit 1
fi

# ----------------------------
# Write Java code to file
SANITIZED_CLASS_NAME=$(echo "$CLASS_NAME" | tr ' ' '_')
JAVA_FILE_PATH="$SCRIPT_DIR/$OUTPUT_DIR/${SANITIZED_CLASS_NAME}.java"

echo "$CODE_BLOCK" > "$JAVA_FILE_PATH"
echo "Java file saved as: $JAVA_FILE_PATH"

# ----------------------------
# Compile Java file
echo "Compiling Java file..."
javac "$JAVA_FILE_PATH"
if [ $? -ne 0 ]; then
    echo "Compilation failed."
    STATUS="compile error"
else
    echo "Compilation succeeded."
    STATUS="success"
fi

# ----------------------------
# Write result to main result.csv
write_result_to_csv
