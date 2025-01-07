import os
import requests
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright
from markdownify import markdownify as md

# Configuration
SAVE_PATH = "./IDFspokesman"

# Helper functions
def sanitize_url(url):
    """Remove query strings from a URL."""
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

def is_relevant_image(url):
    """Check if the image is relevant (e.g., ignore icons like 'ico-download-small')."""
    irrelevant_keywords = ["ico-download-small"]
    return all(keyword not in url for keyword in irrelevant_keywords)

def download_url_content(url, folder_path):
    """Download content from a URL using Playwright and preserve structure in markdown."""
    content = []
    base_url = "https://www.idf.il/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)

            # Extract title
            title = page.query_selector(".heading-default.h1-heading")
            if title:
                content.append(f"# {title.inner_text().strip()}")

            # Extract content in .col-md-12.column
            columns = page.query_selector_all(".col-md-12.column")
            for column in columns:
                column_html = column.inner_html()
                column_content = md(column_html)

                # Embed images within the column
                img_tags = column.query_selector_all("img")
                for img in img_tags:
                    img_url = img.get_attribute("src")
                    img_alt = img.get_attribute("alt") or "Image"
                    if img_url and is_relevant_image(img_url):
                        img_url = sanitize_url(urljoin(base_url, img_url))
                        column_content += f"\n\n![{img_alt}]({img_url})"

                # Embed videos within the column
                iframes = column.query_selector_all("iframe")
                for iframe in iframes:
                    src = iframe.get_attribute("src")
                    if src and ("youtube.com" in src or "youtu.be" in src):
                        column_content += f'\n\n<iframe src="{src}" width="600" height="337" frameborder="0" allowfullscreen></iframe>'

                content.append(column_content)

            # Handle carousel images
            sliders = page.query_selector_all(".image-slider .item-slide")
            for slider in sliders:
                img = slider.query_selector("img")
                if img:
                    img_url = img.get_attribute("src")
                    img_alt = img.get_attribute("alt") or "Carousel Image"
                    if img_url and is_relevant_image(img_url):
                        img_url = sanitize_url(urljoin(base_url, img_url))
                        content.append(f"![{img_alt}]({img_url})")

        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
        finally:
            browser.close()

    return "\n\n".join(content)

def append_to_markdown(md_filename, additional_content):
    """Append additional content to an existing markdown file."""
    with open(md_filename, "a", encoding="utf-8") as f:
        f.write("\n\n" + additional_content)

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
                        page_content = download_url_content(link, folder_path)
                        scraped_content.append(page_content)
                    except Exception as e:
                        print(f"Failed to scrape {link}: {e}")

                if scraped_content:
                    additional_content = "\n\n".join(scraped_content)
                    append_to_markdown(md_filename, additional_content)

if __name__ == "__main__":
    process_message_files()
