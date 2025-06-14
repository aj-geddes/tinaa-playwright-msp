#!/usr/bin/env python3
"""
Fix broken external links in documentation.
"""

import re
from pathlib import Path

# Map of broken links to their replacements
LINK_REPLACEMENTS = {
    # Remove non-existent external resources
    "https://tinaa-playwright.readthedocs.io/": "#",
    "https://hub.docker.com/r/tinaa/playwright-msp": "#",
    "https://github.com/aj-geddes/tinaa-playwright-msp/discussions": "https://github.com/aj-geddes/tinaa-playwright-msp/issues",
    "https://github.com/aj-geddes/tinaa-playwright-msp/discussions/categories/developers": "https://github.com/aj-geddes/tinaa-playwright-msp/issues",
    "https://github.com/aj-geddes/tinaa-playwright-msp/discussions/categories/ideas": "https://github.com/aj-geddes/tinaa-playwright-msp/issues",
    "https://github.com/aj-geddes/tinaa-playwright-msp/discussions/categories/q-a": "https://github.com/aj-geddes/tinaa-playwright-msp/issues",
    "https://github.com/aj-geddes/tinaa-playwright-msp/discussions/categories/show-and-tell": "https://github.com/aj-geddes/tinaa-playwright-msp/issues",
    "https://github.com/tinaa-examples/sdk-development": "#",
    "https://github.com/tinaa-examples/custom-patterns": "#",
    "https://marketplace.tinaa.dev/": "#",
    "https://aj-geddes.github.io/tinaa-playwright-msp/": "#",
    "https://github.com/aj-geddes/tinaa-playwright-msp/docs": "https://github.com/aj-geddes/tinaa-playwright-msp",
    "https://github.com/aj-geddes/tinaa-playwright-msp/blob/main/CODE_OF_CONDUCT.md": "#",
    "https://tinaa.dev/blog": "#",
    "https://tinaa.dev/feedback": "#",
    "https://tinaa.dev/newsletter": "#",
    "https://youtube.com/@tinaa-testing": "#",
    "https://stackoverflow.com/questions/tagged/tinaa": "#",
    "https://stackoverflow.com/questions/ask?tags=tinaa": "#",
    "file:///home/runner/work/tinaa-playwright-msp/tinaa-playwright-msp/docs/LICENSE": "https://github.com/aj-geddes/tinaa-playwright-msp/blob/main/LICENSE",
}

def fix_links_in_file(file_path: Path) -> bool:
    """Fix broken links in a single file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Replace each broken link
        for broken_link, replacement in LINK_REPLACEMENTS.items():
            if broken_link in content:
                content = content.replace(broken_link, replacement)
        
        # Write back if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
            
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    root_path = Path("/mnt/c/Users/Munso/tinaa-playwright-msp")
    
    # Get all markdown files
    md_files = []
    for pattern in ["*.md", "docs/**/*.md"]:
        md_files.extend(root_path.glob(pattern))
    
    # Filter out venv and cache
    md_files = [f for f in md_files if "venv" not in str(f) and ".pytest_cache" not in str(f)]
    
    fixed_files = []
    
    for md_file in md_files:
        if fix_links_in_file(md_file):
            fixed_files.append(str(md_file.relative_to(root_path)))
    
    if fixed_files:
        print(f"Fixed broken links in {len(fixed_files)} files:")
        for f in fixed_files:
            print(f"  {f}")
    else:
        print("No broken links found to fix!")
    
    return fixed_files

if __name__ == "__main__":
    main()