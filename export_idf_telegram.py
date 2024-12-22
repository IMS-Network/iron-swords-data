import os
import boto3
from dotenv import load_dotenv
import shutil
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import json
from datetime import datetime, timezone
import time
import argparse
import subprocess

# Load environment variables from a .env file
load_dotenv()

# Configuration
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHANNEL = "@idf_telegram"
SAVE_PATH = "./IDFspokesman"
STATE_FILE = "last_message_state.json"
START_DATE = datetime(2023, 10, 7, tzinfo=timezone.utc)  # Start scraping from this date (UTC)
FILE_SIZE_THRESHOLD_MB = 25
PUBLIC_URL_PREFIX = "https://data.iron-swords.co.il/"

# Initialize the S3 client for Cloudflare R2
s3_client = boto3.client(
    "s3",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    endpoint_url=R2_ENDPOINT_URL,
)

# Initialize Telegram client
client = TelegramClient("user_session", API_ID, API_HASH)

# Argument parsing
parser = argparse.ArgumentParser(description="Telegram scraping script.")
parser.add_argument("--last-id", action="store_true", help="Print the last scraped message ID and exit.")
args = parser.parse_args()

# Function to load the last scraped message ID
def load_last_message_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            return state.get("last_message_id", 0)
    return 0

# Function to save the last scraped message ID
def save_last_message_id(last_id):
    state = {"last_message_id": last_id}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# Git functions
def git_commit_and_push(branch_name, message_id):
    try:
        # Ensure the main branch is up-to-date
        subprocess.run(["git", "fetch", "origin", "main"], check=True)

        # Create and switch to a new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # Add changes
        subprocess.run(["git", "add", "."], check=True)

        # Commit changes
        commit_message = f"Processed message ID {message_id}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        # Push branch
        subprocess.run(["git", "push", "--set-upstream", "origin", branch_name], check=True)
        print(f"Committed and pushed changes for branch {branch_name}")

        # Debugging: Ensure there are commits in the branch
        result = subprocess.run(["git", "log", "--oneline", f"{branch_name}...main"], check=True, capture_output=True, text=True)
        print(f"Diff between {branch_name} and main:\n{result.stdout}")

        # Create a PR using GitHub CLI
        pr_title = f"Processed message ID {message_id}"
        pr_body = f"Processed Telegram messages up to ID {message_id}. Automatic PR generated by the script."
        subprocess.run(["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--base", "main"], check=True)
        print(f"Pull request created for branch {branch_name}")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        raise

# Function to download and process media
def download_media(media, folder_path, filename_prefix):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    # Determine the file name based on media type
    if isinstance(media, MessageMediaPhoto):
        filename = f"{filename_prefix}_photo.jpg"
    elif isinstance(media, MessageMediaDocument):
        filename = f"{filename_prefix}_media.mp4" if 'video' in media.document.mime_type else f"{filename_prefix}_media"
    else:
        print(f"Unsupported media type for message {filename_prefix}, skipping.")
        return None

    file_path = os.path.join(folder_path, filename)

    # Retry logic for downloading media
    for attempt in range(3):
        try:
            print(f"Attempting to download media to: {file_path} (Attempt {attempt + 1})")
            client.download_media(media, file=file_path)
            if os.path.exists(file_path):
                print(f"Media successfully downloaded: {file_path}")
                return file_path
        except Exception as e:
            print(f"Download attempt {attempt + 1} failed for {file_path}: {e}")
            time.sleep(2)  # Retry delay

    print(f"Media download failed after retries for {file_path}")
    return None

# Function to process messages
def process_messages():
    print("Starting Telegram scraping...")
    last_message_id = load_last_message_id()
    print(f"Last scraped message ID: {last_message_id}")

    with client:
        for message in client.iter_messages(CHANNEL, offset_id=last_message_id, reverse=True):
            if not message.date or message.date < START_DATE:
                continue

            if not message.message and not message.media:
                continue

            message_date = message.date.astimezone(timezone.utc)
            year = message_date.year
            month_name = message_date.strftime("%B")
            day = message_date.day
            message_id = message.id

            day_folder = os.path.join(SAVE_PATH, str(year), month_name, f"{day:02}")
            os.makedirs(day_folder, exist_ok=True)
            md_filename = os.path.join(day_folder, f"{message_id}.md")
            media_folder = os.path.join(day_folder, str(message_id))

            media_links = {}
            if message.media:
                media_filename = download_media(message.media, media_folder, f"{message_id}")
                if media_filename:
                    relative_path = os.path.relpath(media_filename, day_folder).replace("\\", "/")
                    if os.path.getsize(media_filename) > FILE_SIZE_THRESHOLD_MB * 1024 * 1024:
                        r2_link = upload_to_r2(media_filename, R2_BUCKET_NAME)
                        if r2_link:
                            media_links[relative_path] = r2_link
                            os.remove(media_filename)
                            print(f"Deleted local file: {media_filename}")
                    else:
                        media_links[relative_path] = relative_path

            md_content = f"## Message {message_id}\n\n{message.message or ''}\n\n"
            for original, new_link in media_links.items():
                if new_link.endswith(".jpg"):
                    md_content += f"![Photo]({new_link})\n"
                elif new_link.endswith(".mp4"):
                    md_content += f"![Video]({new_link})\n"

            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"Saved message {message_id} to {md_filename}")

            # Save last processed message ID immediately
            save_last_message_id(message_id)

            # Commit changes and create PR for each message
            branch_name = f"sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}-id-{message_id}"
            git_commit_and_push(branch_name, message_id)

    print(f"Finished scraping, last message ID: {last_message_id}")

# Handle --last-id argument
if args.last_id:
    print(load_last_message_id())
    exit(0)

if __name__ == "__main__":
    process_messages()
