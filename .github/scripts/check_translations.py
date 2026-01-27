#!/usr/bin/env python3
"""
Script to check translation files synchronization.
Compares all JSON translation files against the source (fr.json) to ensure
all keys are present in all files.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set


def load_json_file(file_path: Path) -> Dict:
    """Load a JSON file and return its content as a dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested_keys(data: Dict, parent_key: str = '') -> Set[str]:
    """Recursively extract all nested keys from a dictionary."""
    keys = set()
    for key, value in data.items():
        current_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            keys.update(get_nested_keys(value, current_key))
        else:
            keys.add(current_key)
    return keys


def compare_keys(source_keys: Set[str], target_keys: Set[str], target_file: Path) -> List[str]:
    """Compare source keys with target keys and return missing keys."""
    missing_keys = source_keys - target_keys
    return list(missing_keys)


def main() -> int:
    """Main function to check translation files."""
    # Define the path to the translations directory
    translations_dir = Path(__file__).parent.parent.parent / "custom_components" / "boks" / "translations"

    # Check if translations directory exists
    if not translations_dir.exists():
        print(f"Error: Translations directory not found at {translations_dir}")
        return 1

    # Define the source file (French)
    source_file = translations_dir / "fr.json"

    # Check if source file exists
    if not source_file.exists():
        print(f"Error: Source file not found at {source_file}")
        return 1

    # Load source file and extract keys
    try:
        source_data = load_json_file(source_file)
        source_keys = get_nested_keys(source_data)
        print(f"Source file {source_file.name} has {len(source_keys)} keys")
    except Exception as e:
        print(f"Error loading source file {source_file}: {e}")
        return 1

    # Track all issues found
    all_issues = {}
    error_count = 0

    # Iterate through all JSON files in the translations directory
    for translation_file in translations_dir.glob("*.json"):
        # Skip the source file
        if translation_file.name == source_file.name:
            continue

        try:
            # Load target file and extract keys
            target_data = load_json_file(translation_file)
            target_keys = get_nested_keys(target_data)

            # Compare keys
            missing_keys = compare_keys(source_keys, target_keys, translation_file)
            if missing_keys:
                all_issues[translation_file.name] = sorted(missing_keys)
                error_count += len(missing_keys)

        except Exception as e:
            print(f"Error processing file {translation_file}: {e}")
            error_count += 1

    # Print detailed report
    if all_issues:
        print("\nMissing keys report:")
        print("=" * 50)
        for file_name, missing_keys in all_issues.items():
            print(f"\n{file_name}:")
            for key in missing_keys:
                print(f"  - {key}")
        print(f"\nTotal missing keys: {error_count}")
        print("\nTranslation check failed: Some files are missing keys!")
        return 1
    else:
        print("\nAll translation files are synchronized!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
