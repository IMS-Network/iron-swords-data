import os
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Configuration
SAVE_PATH = "./IDFspokesman"

# Helper Functions
def sanitize_url(url):
    """Remove query strings from a URL."""
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

def is_relevant_image(url):
    """Check if the image is relevant (e.g., ignore icons like 'ico-download-small')."""
    irrelevant_keywords = ["ico-download-small"]
    return all(keyword not in url for keyword in irrelevant_keywords)

def parse_html_content(html, base_url):
    """Parse HTML content and return markdown while maintaining structure."""
    soup = BeautifulSoup(html, "html.parser")
    markdown_parts = []

    for element in soup.children:
        if element.name == "p":  # Text content
            markdown_parts.append(element.get_text().strip())
        elif element.name == "iframe":  # YouTube video
            src = element.get("src")
            if src and ("youtube.com" in src or "youtu.be" in src):
                markdown_parts.append(f'<iframe src="{src}" width="600" height="337" frameborder="0" allowfullscreen></iframe>')
        elif element.name == "img":  # Inline image
            img_url = element.get("src")
            alt_text = element.get("alt", "Image")
            if img_url and is_relevant_image(img_url):
                img_url = sanitize_url(urljoin(base_url, img_url))
                markdown_parts.append(f"![{alt_text}]({img_url})")
        elif element.name == "div" and "image-slider" in element.get("class", []):  # Carousel
            images = element.select("img")
            for img in images:
                img_url = img.get("src")
                alt_text = img.get("alt", "Carousel Image")
                if img_url and is_relevant_image(img_url):
                    img_url = sanitize_url(urljoin(base_url, img_url))
                    markdown_parts.append(f"![{alt_text}]({img_url})")

    return "\n\n".join(markdown_parts)

def download_url_content(url):
    """Download and parse content from the given URL."""
    base_url = "https://www.idf.il/"
    content = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)
            # Extract title
            title = page.query_selector(".heading-default.h1-heading")
            if title:
                content.append(f"# {title.inner_text().strip()}")

            # Extract main content
            columns = page.query_selector_all(".col-md-12.column")
            for column in columns:
                html = column.inner_html()
                content.append(parse_html_content(html, base_url))

        except Exception as e:
            print(f"Error scraping {url}: {e}")
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
                        page_content = download_url_content(link)
                        scraped_content.append(page_content)
                    except Exception as e:
                        print(f"Failed to scrape {link}: {e}")

                if scraped_content:
                    additional_content = "\n\n".join(scraped_content)
                    append_to_markdown(md_filename, additional_content)

if __name__ == "__main__":
    process_message_files()
