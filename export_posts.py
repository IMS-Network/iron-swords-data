import requests
import os
import json
from datetime import datetime
from pathlib import Path

API_URL = os.getenv("API_URL") 
USERNAME = os.getenv("USERNAME")
APP_PASSWORD = os.getenv("APP_PASSWORD") 
GITHUB_REPO_PATH = "./Website"

import base64
auth_string = f"{USERNAME}:{APP_PASSWORD}"
auth_token = base64.b64encode(auth_string.encode()).decode()

HEADERS = {
    "Authorization": f"Basic {auth_token}"
}

def fetch_posts():
    response = requests.get(API_URL, headers=HEADERS)
    response.raise_for_status()
    return response.json()

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
        with open(post_path, "w") as f:
            json.dump(post, f, indent=4)

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
            if relative_path.parts and (relative_path.parts[-2], relative_path.parts[-1], file) not in existing_posts:
                os.remove(os.path.join(root, file))

if __name__ == "__main__":
    posts = fetch_posts()
    organize_posts(posts)
    remove_deleted_posts(posts)
