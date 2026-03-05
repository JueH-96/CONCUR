#!/usr/bin/env python3

import json
import os
import re
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class JPFValidatorV4:
    """JPF Validator V4 - Fixed Version"""

    def __init__(self, generated_code_dir: str = None,
                 jpf_core_dir: str = "./jpf-core"):
        # Use relative path: Generated_Code under current directory
        if generated_code_dir is None:
            script_dir = os.getcwd()
            self.generated_code_dir = os.path.join(script_dir, "Generated_Code")
        else:
            self.generated_code_dir = generated_code_dir

        self.jpf_core_dir = Path(jpf_core_dir).resolve()
        self.jpf_bin_dir = self.jpf_core_dir / "bin"
        self.jpf_bin = self.jpf_bin_dir / "jpf"
        self.examples_dir = self.jpf_core_dir / "src" / "examples"
        self.temp_compile_dir = "./temp_compile"

        # Check whether JPF exists
        if not self.jpf_core_dir.exists():
            print(f"Error: JPF core directory not found: {self.jpf_core_dir}")
            sys.exit(1)

        if not self.jpf_bin.exists():
            print(f"Error: JPF binary not found: {self.jpf_bin}")
            print("Please ensure jpf-core is properly set up")
            sys.exit(1)

    def setup_directories(self):
        """Create required directories"""
        # Ensure JPF examples directory exists
        self.examples_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary compilation directory
        os.makedirs(self.temp_compile_dir, exist_ok=True)

    def clean_examples_directory(self):
        """Clear the examples directory"""
        if self.examples_dir.exists():
            for item in self.examples_dir.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"  Warning: Failed to delete {item}: {e}")

    def build_jpf_project(self) -> bool:
        """
        Build the JPF project
        Using ./gradlew clean buildJar
        Reference implementation: run_jpf_one.py
        """
        print("  Building JPF project...", end=" ", flush=True)

        try:
            subprocess.run(
                ["./gradlew", "clean"],
                cwd=self.jpf_core_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=60
            )

            subprocess.run(
                ["./gradlew", "buildJar"],
                cwd=self.jpf_core_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=120
            )

            print("OK")
            return True

        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            return False
        except subprocess.CalledProcessError as e:
            print(f"FAILED (exit code: {e.returncode})")
            return False
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def extract_class_name(self, java_code: str) -> str:
        """
        Extract the public class name from Java code
        """
        pattern = r'\bpublic\s+class\s+(\w+)'
        match = re.search(pattern, java_code)

        if match:
            return match.group(1)

        pattern = r'\bclass\s+(\w+)'
        match = re.search(pattern, java_code)

        if match:
            return match.group(1)

        return None

    def compile_java_code(self, java_code: str, class_name: str) -> Tuple[bool, str]:
        """
        Compile Java code using javac for basic syntax validation

        Returns: (success, error_message)
        """
        java_file = os.path.join(self.temp_compile_dir, f"{class_name}.java")

        try:
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(java_code)

            result = subprocess.run(
                ['javac', java_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, ""
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Compilation timeout"
        except Exception as e:
            return False, str(e)
        finally:
            if os.path.exists(java_file):
                os.remove(java_file)

            class_file = os.path.join(self.temp_compile_dir, f"{class_name}.class")
            if os.path.exists(class_file):
                os.remove(class_file)

    def create_jpf_config(self, class_name: str, max_depth: str) -> Path:
        """
        Create a JPF configuration file

        Returns: path to the JPF config file
        """
        jpf_content = f"""target={class_name}
+vm.fast.startup
listener=gov.nasa.jpf.listener.ThreadCountListener,gov.nasa.jpf.listener.TimeLimitListener,gov.nasa.jpf.listener.StarvationListener,gov.nasa.jpf.listener.PreciseRaceDetector,gov.nasa.jpf.listener.DeadlockAnalyzer
timeLimitMillis=9000
search.depth_limit = {max_depth if max_depth else '300'}
"""

        jpf_file = self.examples_dir / f"{class_name}.jpf"

        with open(jpf_file, 'w', encoding='utf-8') as f:
            f.write(jpf_content)

        return jpf_file

    def run_jpf(self, class_name: str) -> Tuple[str, str]:
        """
        Run JPF verification

        Execution method:
        1. Run inside jpf-core/bin
        2. Use relative path: jpf ../src/examples/ClassName.jpf

        Returns: (jpf_result, jpf_details)
        """
        try:
            rel_jpf_path = Path("../src/examples") / f"{class_name}.jpf"

            result = subprocess.run(
                [str(self.jpf_bin), str(rel_jpf_path)],
                cwd=self.jpf_bin_dir,
                capture_output=True,
                text=True,
                timeout=40,
            )

            output = result.stdout + result.stderr

            jpf_result = self.extract_jpf_result(output)
            jpf_details = self.extract_jpf_details(output)

            return jpf_result, jpf_details

        except subprocess.TimeoutExpired:
            return "timeout", "JPF execution timeout after 40 seconds"
        except Exception as e:
            return "error", f"JPF execution error: {str(e)}"

    def extract_jpf_result(self, output: str) -> str:
        """
        Extract result section from JPF output

        Content between:
        ====== results
        ====== statistics

        If not found, return first 5 and last 5 lines
        """
        pattern = r'={5,}\s*results\s*\n(.*?)\n={5,}\s*statistics'
        match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)

        if match:
            result = match.group(1).strip()
            return result if result else "no errors detected"

        lines = output.strip().split('\n')

        if lines:
            non_empty_lines = [line for line in lines if line.strip()]

            if len(non_empty_lines) <= 10:
                return '\n'.join(non_empty_lines)
            else:
                first_five = non_empty_lines[:5]
                last_five = non_empty_lines[-5:]
                return '\n'.join(first_five) + '\n...\n' + '\n'.join(last_five)

        return "empty output"

    def extract_jpf_details(self, output: str) -> str:
        """
        Extract detailed information from JPF output

        Starting from:
        "Unique logical threads created during execution:"

        Remove:
        - lines containing "elapsed time:"
        - timestamp after "search finished:"
        """
        lines = output.split('\n')

        for i, line in enumerate(lines):
            if "Unique logical threads created during execution:" in line:
                details_lines = lines[i:]
                filtered_lines = [l for l in details_lines if 'elapsed time:' not in l.lower()]
                cleaned_lines = self._remove_search_finished_timestamp(filtered_lines)
                return '\n'.join(cleaned_lines).strip()

        if len(lines) > 10:
            last_lines = lines[-10:]
        else:
            last_lines = lines

        filtered_lines = [l for l in last_lines if 'elapsed time:' not in l.lower()]
        cleaned_lines = self._remove_search_finished_timestamp(filtered_lines)

        return '\n'.join(cleaned_lines).strip()

    def _remove_search_finished_timestamp(self, lines: List[str]) -> List[str]:
        """
        Remove timestamp after "search finished"

        Example:
        "search finished: 11/16/25 9:26 AM"
        -> "search finished"
        """
        cleaned_lines = []

        for line in lines:
            cleaned_line = re.sub(
                r'(search finished):\s+.*',
                r'\1',
                line,
                flags=re.IGNORECASE
            )
            cleaned_lines.append(cleaned_line)

        return cleaned_lines