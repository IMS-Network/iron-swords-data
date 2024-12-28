import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import json
from datetime import datetime, timezone

# Load environment variables from a .env file
load_dotenv()

# Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
NEW_CHANNEL = "@tzevaadomm"  # Replace with the new Telegram channel handle
SAVE_PATH = "./Tzevaadomm"
STATE_FILE = "tzevaadomm_id.json"
START_DATE = datetime(2023, 10, 7, tzinfo=timezone.utc)  # Start scraping from this date (UTC)

# Initialize Telegram client
client = TelegramClient("new_channel_session", API_ID, API_HASH)

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
        filename = f"{filename_prefix}_photo.jpg"
    elif isinstance(media, MessageMediaDocument):
        filename = f"{filename_prefix}_media.mp4" if 'video' in media.document.mime_type else f"{filename_prefix}_media"
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

    daily_messages = {}
    with client:
        for message in client.iter_messages(NEW_CHANNEL, offset_id=last_message_id, reverse=True):
            if not message.date or message.date < START_DATE:
                continue

            if not message.message and not message.media:
                continue

            message_date = message.date.astimezone(timezone.utc)
            date_key = message_date.strftime("%Y-%m-%d")
            timestamp = message_date.strftime("%H:%M")

            if date_key not in daily_messages:
                daily_messages[date_key] = []

            entry = {"timestamp": timestamp, "text": message.message, "media": None}

            if message.media:
                media_folder = os.path.join(SAVE_PATH, date_key)
                os.makedirs(media_folder, exist_ok=True)
                media_filename = download_media(message.media, media_folder, f"{message.id}")
                if media_filename:
                    relative_path = os.path.relpath(media_filename, SAVE_PATH).replace("\\", "/")
                    entry["media"] = relative_path

            daily_messages[date_key].append(entry)
            last_message_id = message.id

    # Save daily messages to Markdown files
    for date_key, messages in daily_messages.items():
        day_folder = os.path.join(SAVE_PATH, date_key)
        os.makedirs(day_folder, exist_ok=True)
        md_filename = os.path.join(day_folder, f"{date_key}.md")

        with open(md_filename, "w", encoding="utf-8") as f:
            for message in messages:
                f.write(f"# {message['timestamp']}\n\n")
                if message['text']:
                    f.write(f"{message['text']}\n\n")
                if message['media']:
                    if message['media'].endswith(".jpg"):
                        f.write(f"![Photo]({message['media']})\n\n")
                    elif message['media'].endswith(".mp4"):
                        f.write(f"![Video]({message['media']})\n\n")

        print(f"Saved daily messages to {md_filename}")

    save_last_message_id(last_message_id)
    print(f"Finished scraping, last message ID: {last_message_id}")

if __name__ == "__main__":
    process_messages()
    print("Telegram scraping completed successfully.")
