import os
import requests
from playwright.sync_api import sync_playwright

# Configuration
SAVE_PATH = "./IDFspokesman"

# Helper functions
def download_url_content(url, folder_path):
    """Download content from a URL using Playwright and requests."""
    content = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)
            if "videoidf.azureedge.net" in url:
                # Extract video URL
                video_tag = page.query_selector("video source")
                if video_tag:
                    video_url = video_tag.get_attribute("src")
                    if video_url:
                        video_filename = os.path.join(folder_path, os.path.basename(video_url))
                        # Use requests to download video
                        video_response = requests.get(video_url, stream=True)
                        with open(video_filename, "wb") as f:
                            for chunk in video_response.iter_content(1024):
                                f.write(chunk)
                        content.append(f"[Video]({video_filename})")
            elif "idfanc.activetrail.biz" in url:
                # Extract content from .bl-block-content
                block_content = page.query_selector_all(".bl-block-content")
                for block in block_content:
                    content.append(block.inner_text())
            else:
                # Extract general text content
                holder_content = page.query_selector_all(".holder")
                for holder in holder_content:
                    content.append(holder.inner_text())
                # Extract images
                img_tags = page.query_selector_all("img")
                for img in img_tags:
                    img_url = img.get_attribute("src")
                    if img_url and img_url.startswith("http"):
                        img_filename = os.path.join(folder_path, os.path.basename(img_url))
                        img_response = requests.get(img_url, stream=True)
                        with open(img_filename, "wb") as f:
                            for chunk in img_response.iter_content(1024):
                                f.write(chunk)
                        content.append(f"![Image]({img_filename})")
                # Extract YouTube videos
                iframes = page.query_selector_all("iframe")
                for iframe in iframes:
                    src = iframe.get_attribute("src")
                    if src and ("youtube.com" in src or "youtu.be" in src):
                        content.append(f"[YouTube Video]({src})")
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
        finally:
            browser.close()

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
                links = []
                for line in content.splitlines():
                    if line.startswith("http"):
                        parts = line.split(" ")
                        if len(parts) > 0:
                            links.append(parts[0])

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
