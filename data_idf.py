import os
import requests
from bs4 import BeautifulSoup

# Configuration
SAVE_PATH = "./IDFspokesman"

# Helper functions
def download_url_content(url, folder_path):
    """Download content from a URL, including images and YouTube videos."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    content = []

    # Download images
    for img in soup.find_all("img"):
        img_url = img.get("src")
        if img_url:
            img_response = requests.get(img_url, stream=True)
            img_filename = os.path.join(folder_path, os.path.basename(img_url))
            with open(img_filename, "wb") as f:
                for chunk in img_response.iter_content(1024):
                    f.write(chunk)
            content.append(f"![Image]({img_filename})")

    # Embed YouTube videos
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if "youtube.com" in src or "youtu.be" in src:
            content.append(f"[YouTube Video]({src})")

    # Extract article text
    for p in soup.find_all("p"):
        content.append(p.text.strip())

    return "\n\n".join(content)

def append_to_markdown(md_filename, additional_content):
    """Append additional content to an existing markdown file."""
    with open(md_filename, "a", encoding="utf-8") as f:
        f.write(additional_content)

def process_message_files():
    """Process each message file in the folder, scrape content from links, and append to the markdown."""
    for root, _, files in os.walk(SAVE_PATH):
        for file in files:
            if file.endswith(".md"):
                md_filename = os.path.join(root, file)
                print(f"Processing file: {md_filename}")

                with open(md_filename, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract links from the markdown content
                links = [line.split(" ")[1] for line in content.splitlines() if line.startswith("http")]

                if not links:
                    continue

                scraped_content = []
                for link in links:
                    print(f"Scraping link: {link}")
                    try:
                        folder_path = os.path.dirname(md_filename)
                        content = download_url_content(link, folder_path)
                        scraped_content.append(content)
                    except Exception as e:
                        print(f"Failed to scrape {link}: {e}")

                if scraped_content:
                    additional_content = "\n\n".join(scraped_content)
                    append_to_markdown(md_filename, additional_content)

if __name__ == "__main__":
    process_message_files()