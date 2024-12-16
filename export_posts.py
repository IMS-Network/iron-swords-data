import requests
import os
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64

# Configuration
API_URL = os.getenv("API_URL")  # Base URL for posts
USERNAME = os.getenv("USERNAME")
APP_PASSWORD = os.getenv("APP_PASSWORD")
GITHUB_REPO_PATH = "./Website"

# Authentication
auth_string = f"{USERNAME}:{APP_PASSWORD}"
auth_token = base64.b64encode(auth_string.encode()).decode()

HEADERS = {
    "Authorization": f"Basic {auth_token}"
}

# Fetch posts for a single page
def fetch_posts_page(api_url, page):
    response = requests.get(f"{api_url}?per_page=100&page={page}", headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:  # End of available pages
        return []
    else:
        response.raise_for_status()

# Fetch all posts with parallel processing
def fetch_all_posts(api_url):
    all_posts = []
    max_threads = 10  # Adjust based on the number of threads your system can handle
    page = 1

    # First, determine the total number of pages
    response = requests.get(f"{api_url}?per_page=100&page=1", headers=HEADERS)
    response.raise_for_status()
    total_posts = int(response.headers.get("X-WP-Total", 0))
    total_pages = int(response.headers.get("X-WP-TotalPages", 1))
    print(f"Total posts: {total_posts}, Total pages: {total_pages}")

    # Use ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_threads) as executor:
        future_to_page = {
            executor.submit(fetch_posts_page, api_url, page): page for page in range(1, total_pages + 1)
        }

        for future in as_completed(future_to_page):
            try:
                page_posts = future.result()
                all_posts.extend(page_posts)
            except Exception as e:
                print(f"Error fetching page {future_to_page[future]}: {e}")

    return all_posts

# Organize posts into year/month folders
def organize_posts(posts):
    base_path = Path(GITHUB_REPO_PATH)
    base_path.mkdir(parents=True, exist_ok=True)

    for post in posts:
        post_date = datetime.fromisoformat(post["date_gmt"]).astimezone()
        year = post_date.year
        month = post_date.strftime("%B")
        slug = post["slug"]

        year_path = base_path / str(year)
        month_path = year_path / month
        month_path.mkdir(parents=True, exist_ok=True)

        post_path = month_path / f"{slug}.json"

        # Save or overwrite post as JSON
        with open(post_path, "w") as f:
            json.dump(post, f, indent=4)

# Remove posts that no longer exist on WordPress
def remove_deleted_posts(current_posts):
    existing_posts = set()
    for post in current_posts:
        post_date = datetime.fromisoformat(post["date_gmt"]).astimezone()
        year = post_date.year
        month = post_date.strftime("%B")
        slug = post["slug"]

        existing_posts.add((str(year), month, f"{slug}.json"))

    for root, dirs, files in os.walk(GITHUB_REPO_PATH):
        for file in files:
            relative_path = Path(root).relative_to(GITHUB_REPO_PATH)
            if relative_path.parts and (relative_path.parts[-3], relative_path.parts[-2], relative_path.parts[-1]) not in existing_posts:
                os.remove(os.path.join(root, file))

if __name__ == "__main__":
    print("Fetching all posts from WordPress...")
    posts = fetch_all_posts(API_URL)
    print(f"Fetched {len(posts)} posts.")

    print("Organizing posts...")
    organize_posts(posts)

    print("Removing deleted posts...")
    remove_deleted_posts(posts)

    print("Sync complete.")
