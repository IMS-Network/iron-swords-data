import os
import re

# Configuration
ROOT_PATH = "./IDFspokesman"  # Root directory to search for Markdown files
PUBLIC_URL_PREFIX = "https://data.iron-swords.co.il/"  # Correct URL prefix
BROKEN_URL_REGEX = re.compile(r"https://data\.iron-swords\.co\.il/.+?https://data\.iron-swords\.co\.il/")  # Pattern to identify duplicated prefixes

# Function to fix broken URLs in a file
def fix_broken_urls_in_file(md_file_path):
    try:
        with open(md_file_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Replace broken URLs with the correct format
        fixed_content = re.sub(
            BROKEN_URL_REGEX, 
            PUBLIC_URL_PREFIX, 
            content
        )
        
        # Only write back if changes were made
        if content != fixed_content:
            with open(md_file_path, "w", encoding="utf-8") as file:
                file.write(fixed_content)
            print(f"Fixed URLs in: {md_file_path}")
        else:
            print(f"No changes needed: {md_file_path}")
    
    except Exception as e:
        print(f"Error processing {md_file_path}: {e}")

# Function to recursively fix URLs in Markdown files
def fix_broken_urls_in_directory(root_path):
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith(".md"):
                md_file_path = os.path.join(root, file)
                fix_broken_urls_in_file(md_file_path)

if __name__ == "__main__":
    print("Starting to fix broken URLs...")
    fix_broken_urls_in_directory(ROOT_PATH)
    print("URL fixing completed.")
