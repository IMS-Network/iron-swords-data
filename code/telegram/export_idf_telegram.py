import os
import boto3
from dotenv import load_dotenv
import shutil
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import json
from datetime import datetime, timezone
import posixpath  # Ensure consistent URL path formatting

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
SAVE_PATH = "../../IDFspokesman"
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

# Initialize the Telegram client
client = TelegramClient('session_telegram_scraper', API_ID, API_HASH)

# Ensure consistent paths for S3 and URLs
def normalize_file_key(file_path):
    return posixpath.normpath(file_path).replace("\\", "/")

# Determine file type based on extension
def determine_content_type(file_name):
    if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        return "image/jpeg"
    elif file_name.lower().endswith('.mp4'):
        return "video/mp4"
    elif file_name.lower().endswith('.avi'):
        return "video/x-msvideo"
    elif file_name.lower().endswith('.mov'):
        return "video/quicktime"
    else:
        return "application/octet-stream"

# Extract date from the directory structure
def extract_date_from_path(file_key):
    try:
        parts = file_key.split("/")
        if len(parts) >= 3:
            year = parts[0]
            month = parts[1]
            day = parts[2]
            month_number = datetime.strptime(month, "%B").month
            return f"{year}-{month_number:02d}-{int(day):02d}"
        else:
            return None
    except Exception as e:
        print(f"Error extracting date from path '{file_key}': {e}")
        return None

# Function to check if a file exists in the R2 bucket
def file_exists_in_r2(file_key, bucket_name):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except s3_client.exceptions.ClientError:
        return False

# Function to upload media to R2 with metadata updates
def upload_to_r2(file_path, bucket_name):
    try:
        file_key = normalize_file_key(os.path.relpath(file_path, SAVE_PATH))
        if file_exists_in_r2(file_key, bucket_name):
            print(f"File already exists in R2: {file_key}")
            return f"{PUBLIC_URL_PREFIX}{file_key}"
        
        # Extract date from file key
        update_date = extract_date_from_path(file_key)
        if not update_date:
            print(f"Unable to determine update date for {file_key}, skipping metadata update.")

        # Determine Content-Type
        content_type = determine_content_type(file_key)
        file_type = "image" if "image" in content_type else "video"

        # Upload file with metadata
        s3_client.upload_file(
            file_path,
            bucket_name,
            file_key,
            ExtraArgs={
                "ContentType": content_type,
                "Metadata": {
                    "update-date": update_date,
                    "file-type": file_type,
                }
            }
        )
        print(f"Uploaded: {file_path} -> {file_key} with metadata")
        return f"{PUBLIC_URL_PREFIX}{file_key}"
    except Exception as e:
        print(f"Failed to upload {file_path}: {e}")
        return None

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

# Function to download and save media
def download_media(media, folder_path, filename_prefix):
    if isinstance(media, MessageMediaPhoto):
        filename = f"{filename_prefix}.jpg"
    elif isinstance(media, MessageMediaDocument):
        filename = f"{filename_prefix}.mp4" if 'video' in media.document.mime_type else f"{filename_prefix}.file"
    else:
        return None

    file_path = os.path.join(folder_path, filename)
    client.download_media(media, file=file_path)
    return file_path

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

            day_folder = os.path.join(SAVE_PATH, str(year), month_name, f"{day:02}")
            images_folder = os.path.join(day_folder, "images")
            md_filename = os.path.join(day_folder, "alerts.md")

            os.makedirs(images_folder, exist_ok=True)

            timestamp = message_date.strftime("%H:%M")

            # Initialize the Markdown file if it doesn't exist
            if not os.path.exists(md_filename):
                with open(md_filename, "w", encoding="utf-8") as f:
                    f.write(f"# Alerts for {message_date.strftime('%Y-%m-%d')}\n\n")

            # Append message content and media to the Markdown file
            with open(md_filename, "a", encoding="utf-8") as f:
                f.write(f"## {timestamp}\n\n")
                if message.message:
                    f.write(f"{message.message}\n\n")

                if message.media:
                    media_filename = download_media(message.media, images_folder, f"{message.id}")
                    if media_filename:
                        relative_path = os.path.relpath(media_filename, day_folder).replace("\\", "/")
                        if media_filename.endswith(".jpg"):
                            f.write(f"![Photo](images/{os.path.basename(relative_path)})\n\n")
                        elif media_filename.endswith(".mp4"):
                            f.write(f"![Video](images/{os.path.basename(relative_path)})\n\n")

            last_message_id = message.id

    save_last_message_id(last_message_id)
    print(f"Finished scraping, last message ID: {last_message_id}")

# Function to scan and upload existing files
def scan_and_upload_existing():
    for root, _, files in os.walk(SAVE_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            upload_to_r2(file_path, R2_BUCKET_NAME)

if __name__ == "__main__":
    scan_and_upload_existing()
    process_messages()
    print("Telegram scraping completed successfully.")
