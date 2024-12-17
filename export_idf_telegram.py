from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHANNEL = "@idf_telegram"
SAVE_PATH = "./IDFspokesman"
STATE_FILE = "last_message_id.json"

# Initialize client
client = TelegramClient("user_session", API_ID, API_HASH)

# Function to load the last scraped message ID
def load_last_message_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("last_message_id", 0)
    return 0

# Function to save the last scraped message ID
def save_last_message_id(last_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_message_id": last_id}, f)

# Function to download media
def download_media(media, folder_path, filename_prefix):
    if isinstance(media, MessageMediaPhoto):
        filename = f"{filename_prefix}_photo.jpg"
    elif isinstance(media, MessageMediaDocument):
        filename = f"{filename_prefix}_media.mp4" if 'video' in media.document.mime_type else f"{filename_prefix}_media"
    else:
        return None
    client.download_media(media, file=os.path.join(folder_path, filename))
    return filename

# Function to process messages
def process_messages():
    last_message_id = load_last_message_id()
    current_date = datetime.now()
    start_date = current_date.replace(day=1)  # Start of the current month
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)  # End of the current month

    print(f"Scraping messages from {start_date.date()} to {end_date.date()}")

    with client:
        for message in client.iter_messages(CHANNEL, offset_id=last_message_id, reverse=True):
            if message.date < start_date or message.date > end_date:
                continue  # Process messages only for the current month

            if not message.message and not message.media:
                continue

            # Extract message info
            message_date = message.date.astimezone()
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
    print("Starting Telegram scraping...")
    process_messages()
    print("Telegram scraping completed successfully.")
