#!/usr/bin/env python3
"""
Script to generate llms.txt file by reading all Markdown files
from the content/docs directory and combining their content.
"""

import sys
from pathlib import Path


def read_markdown_files(src_dir):
    """
    Recursively read all Markdown files from the source directory.

    Args:
        src_dir (str): Source directory path

    Returns:
        list: List of file contents
    """
    content = []
    src_path = Path(src_dir)

    if not src_path.exists():
        print(f"Error: Directory '{src_dir}' does not exist")
        return content

    # Recursively find all .md files
    for md_file in src_path.rglob("*.md"):
        try:
            with open(md_file, encoding="utf-8") as file:
                txt = file.read()
                content.append(txt)
                print(f"Read: {md_file}")
        except Exception as e:
            print(f"Error reading {md_file}: {e}")

    return content


def main():
    """Main function to generate llms.txt file."""
    print("Generating llms.txt...")

    try:
        # Read all markdown files from /docs (adjusted path for GitHub scripts directory)
        content = read_markdown_files("../../docs")

        if not content:
            print("No Markdown files found or error occurred while reading files.")
            sys.exit(1)

        # Ensure docs directory exists (adjusted path for GitHub scripts directory)
        docs_dir = Path("../../docs")
        docs_dir.mkdir(exist_ok=True)

        # Write combined content to llms.txt
        output_file = docs_dir / "llms.txt"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write("\n\n".join(content))

        print(f"Done generating llms.txt. Combined {len(content)} files.")

    except Exception as err:
        print(f"Error occurred while generating llms.txt: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
