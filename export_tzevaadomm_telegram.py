import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import json
from datetime import datetime, timezone, timedelta

# Load environment variables from a .env file
load_dotenv()

# Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
NEW_CHANNEL = "@tzevaadomm"  # Replace with the new Telegram channel handle
SAVE_PATH = "./Tzevaadomm"
STATE_FILE = "tzevaadomm_id.json"
START_DATE = datetime(2023, 10, 7, tzinfo=timezone.utc)  # Start scraping from this date (UTC)
TIME_THRESHOLD = timedelta(minutes=1)  # Combine messages sent within 1 minute

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

    combined_messages = []
    with client:
        for message in client.iter_messages(NEW_CHANNEL, offset_id=last_message_id, reverse=True):
            if not message.date or message.date < START_DATE:
                continue

            if not message.message and not message.media:
                continue

            message_date = message.date.astimezone(timezone.utc)
            year = message_date.year
            month_name = message_date.strftime("%B")
            day = message_date.day
            message_id = message.id

            # Check if the message should be combined with the last one
            if combined_messages and (message_date - combined_messages[-1]['date']) <= TIME_THRESHOLD:
                combined_messages[-1]['content'].append(message)
            else:
                combined_messages.append({
                    'date': message_date,
                    'content': [message]
                })

    for group in combined_messages:
        group_date = group['date']
        year = group_date.year
        month_name = group_date.strftime("%B")
        day = group_date.day

        day_folder = os.path.join(SAVE_PATH, str(year), month_name, f"{day:02}")
        os.makedirs(day_folder, exist_ok=True)
        md_filename = os.path.join(day_folder, f"{group_date.strftime('%Y%m%d_%H%M%S')}.md")
        media_folder = os.path.join(day_folder, group_date.strftime('%Y%m%d_%H%M%S'))

        os.makedirs(media_folder, exist_ok=True)
        md_content = f"## Combined Messages from {group_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for message in group['content']:
            if message.message:
                md_content += f"{message.message}\n\n"

            if message.media:
                media_filename = download_media(message.media, media_folder, f"{message.id}")
                if media_filename:
                    relative_path = os.path.relpath(media_filename, day_folder).replace("\\", "/")
                    if media_filename.endswith(".jpg"):
                        md_content += f"![Photo]({relative_path})\n"
                    elif media_filename.endswith(".mp4"):
                        md_content += f"![Video]({relative_path})\n"

        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Saved combined message group to {md_filename}")

        last_message_id = max(msg.id for msg in group['content'])

    save_last_message_id(last_message_id)
    print(f"Finished scraping, last message ID: {last_message_id}")

if __name__ == "__main__":
    process_messages()
    print("Telegram scraping completed successfully.")
