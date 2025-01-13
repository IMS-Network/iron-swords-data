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
client = TelegramClient('session_name', API_ID, API_HASH)

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

# Other existing functions remain unchanged...

if __name__ == "__main__":
    scan_and_upload_existing()
    process_messages()
    print("Telegram scraping completed successfully.")
