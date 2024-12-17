import requests
import os
import json
from datetime import datetime, timezone, timedelta
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

        # Path for the post JSON file
        year_path = base_path / str(year)
        month_path = year_path / month
        month_path.mkdir(parents=True, exist_ok=True)
        post_path = month_path / f"{slug}.json"

        # Check if the file exists and if the post has been updated
        if post_path.exists():
            with open(post_path, "r") as f:
                existing_post = json.load(f)
                existing_modified = existing_post.get("modified_gmt", "")
                if existing_modified == post["modified_gmt"]:
                    # No updates, skip this post
                    continue

        # Save or overwrite post as JSON (updated or new)
        with open(post_path, "w") as f:
            json.dump(post, f, indent=4)
        print(f"Updated: {post_path}")

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
            relative_path = Path(root).relative_to(GITHUB_REPO_PATH) / file

            # Ensure the path has at least 3 parts: year/month/slug.json
            if len(relative_path.parts) >= 3:
                year, month, slug_json = relative_path.parts[-3], relative_path.parts[-2], relative_path.parts[-1]
                if (year, month, slug_json) not in existing_posts:
                    os.remove(os.path.join(root, file))
                    print(f"Deleted: {relative_path}")

def process_messages():
    last_message_id = load_last_message_id()
    current_date = datetime.now(timezone.utc)  # Force UTC timezone
    start_date = current_date.replace(day=1)  # Start of the current month (UTC)
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)  # End of the current month

    print(f"Scraping messages from {start_date} to {end_date}")

    with client:
        for message in client.iter_messages(CHANNEL, offset_id=last_message_id, reverse=True):
            if not message.date:
                continue  # Skip messages without a date

            # Convert message.date to UTC-aware datetime
            message_date = message.date.astimezone(timezone.utc)

            if message_date < start_date or message_date > end_date:
                continue  # Skip messages outside the current month

            if not message.message and not message.media:
                continue

            # Extract message info
            year = message_date.year
            month = message_date.strftime("%B")
            day = message_date.day
            message_id = message.id

            # Define paths
            day_folder = os.path.join(SAVE_PATH, str(year), month, f"{day:02}")
            os.makedirs(day_folder, exist_ok=True)
            md_filename = os.path.join(day_folder, f"{message_id}.md")
            media_folder = os.path.join(day_folder, str(message_id))

            # Process media
            media_links = []
            if message.media:
                os.makedirs(media_folder, exist_ok=True)
                media_filename = download_media(message.media, media_folder, f"{message_id}")
                if media_filename:
                    relative_path = os.path.relpath(os.path.join(media_folder, media_filename), day_folder)
                    media_links.append(relative_path)

            # Generate Markdown content
            md_content = f"## Message {message_id}\n\n{message.message or ''}\n\n"
            for media in media_links:
                if media.endswith(".jpg"):
                    md_content += f"![Photo](./{media})\n"
                elif media.endswith(".mp4"):
                    md_content += f"![Video](./{media})\n"

            # Save message content
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"Saved message {message_id} to {md_filename}")

            # Update last message ID
            last_message_id = message_id

    # Save the last processed message ID
    save_last_message_id(last_message_id)
    print(f"Last message ID saved: {last_message_id}")

if __name__ == "__main__":
    print("Fetching all posts from WordPress...")
    posts = fetch_all_posts(API_URL)
    print(f"Fetched {len(posts)} posts.")

    print("Organizing posts...")
    organize_posts(posts)

    print("Removing deleted posts...")
    remove_deleted_posts(posts)

    print("Sync complete.")
