import os
import boto3
from dotenv import load_dotenv
import shutil
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import json
from datetime import datetime, timezone
import time
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

# Function to check if a file exists in R2
def check_r2_file_exists(file_key):
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=file_key)
        print(f"File already exists in R2: {file_key}")
        return True
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            print(f"Error checking file in R2: {e}")
            raise

# Modified upload function to include duplicate checks
def upload_to_r2(file_path, bucket_name):
    file_key = os.path.relpath(file_path, SAVE_PATH).replace("\\", "/")
    if check_r2_file_exists(file_key):
        return f"https://{R2_BUCKET_NAME}.{R2_ENDPOINT_URL}/{file_key}"

    try:
        s3_client.upload_file(file_path, bucket_name, file_key)
        print(f"Uploaded to R2: {file_key}")
        return f"https://{R2_BUCKET_NAME}.{R2_ENDPOINT_URL}/{file_key}"
    except Exception as e:
        print(f"Failed to upload {file_path}: {e}")
        return None

# Git operations
def git_prepare_branch(branch_name):
    subprocess.run(["git", "fetch", "origin", "production"], check=True)
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)

def git_commit_changes(message_id):
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Processed message ID {message_id}"], check=True)

def git_push_branch(branch_name):
    subprocess.run(["git", "push", "--set-upstream", "origin", branch_name], check=True)

def create_pr(branch_name, last_message_id):
    pr_title = f"Processed Telegram messages up to ID {last_message_id}"
    pr_body = f"Processed Telegram messages up to ID {last_message_id}. This PR includes all changes."
    subprocess.run(["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--base", "production"], check=True)

# Download and process media
def download_media(media, folder_path, filename_prefix):
    if isinstance(media, MessageMediaPhoto):
        filename = f"{filename_prefix}_photo.jpg"
    elif isinstance(media, MessageMediaDocument):
        filename = f"{filename_prefix}_media.mp4" if 'video' in media.document.mime_type else f"{filename_prefix}_media"
    else:
        return None

# Main processing function
def process_messages():
    print("Starting Telegram scraping...")
    last_message_id = load_last_message_id()
    print(f"Last scraped message ID: {last_message_id}")

    with client:
        # Iterate messages starting from the last processed message ID
        for message in client.iter_messages(CHANNEL, offset_id=last_message_id, reverse=False):
            try:
                if not message.date or message.date < START_DATE:
                    continue
                if not message.message and not message.media:
                    continue

                message_date = message.date.astimezone(timezone.utc)
                year, month, day = message_date.year, message_date.strftime("%B"), f"{message_date.day:02}"
                message_id = message.id

                # Ensure IDs are sequential
                if last_message_id and message_id != last_message_id + 1:
                    print(f"Skipped message IDs from {last_message_id} to {message_id}")

                last_message_id = message_id  # Update last processed message ID

                day_folder = os.path.join(SAVE_PATH, str(year), month, day)
                os.makedirs(day_folder, exist_ok=True)
                md_filename = os.path.join(day_folder, f"{message_id}.md")

                media_links = {}
                if message.media:
                    media_folder = os.path.join(day_folder, str(message_id))
                    media_file = download_media(message.media, media_folder, str(message_id))
                    if media_file:
                        try:
                            if os.path.getsize(media_file) > FILE_SIZE_THRESHOLD_MB * 1024 * 1024:
                                r2_link = upload_to_r2(media_file, R2_BUCKET_NAME)
                                if r2_link:
                                    os.remove(media_file)
                                    media_links["r2"] = r2_link
                            else:
                                media_links["local"] = os.path.relpath(media_file, SAVE_PATH).replace("\\", "/")
                        except FileNotFoundError:
                            print(f"File not found locally: {media_file}")
                            continue

                md_content = f"## Message {message_id}\n\n{message.message or ''}\n\n"
                for link_type, link in media_links.items():
                    md_content += f"[{link_type.capitalize()} Media]({link})\n"

                with open(md_filename, "w", encoding="utf-8") as f:
                    f.write(md_content)

                # Save last processed message ID
                save_last_message_id(message_id)
                git_commit_changes(message_id)
            except Exception as e:
                print(f"Error processing message ID {message.id}: {e}")

    # Push changes and create PR
    git_push_branch(branch_name)
    create_pr(branch_name, last_message_id)

if __name__ == "__main__":
    scan_and_upload_existing()
    process_messages()
    print("Telegram scraping completed successfully.")