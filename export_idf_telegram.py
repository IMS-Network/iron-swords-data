from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHANNEL = "@idf_telegram"
SAVE_PATH = "./IDFspokesman"
STATE_FILE = "last_message_state.json"
START_DATE = datetime(2023, 10, 7, tzinfo=timezone.utc)  # Start scraping from this date (UTC)

# Initialize client
client = TelegramClient("user_session", API_ID, API_HASH)

# Function to load the last scraped message ID
def load_last_message_id(year, month):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            return state.get(f"{year}-{month}", 0)
    return 0

# Function to save the last scraped message ID
def save_last_message_id(year, month, last_id):
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    state[f"{year}-{month}"] = last_id
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

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

# Function to process messages for a single month
def process_month(year, month):
    print(f"Scraping messages for {year}-{month:02}")
    last_message_id = load_last_message_id(year, month)

    # Calculate start and end dates for the month
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    with client:
        for message in client.iter_messages(CHANNEL, offset_id=last_message_id, reverse=True):
            if not message.date:
                continue

            # Convert message.date to UTC-aware datetime
            message_date = message.date.astimezone(timezone.utc)

            # Stop if message is outside the current month
            if message_date < start_date or message_date > end_date:
                continue

            if not message.message and not message.media:
                continue

            # Extract message info
            year = message_date.year
            month_name = message_date.strftime("%B")
            day = message_date.day
            message_id = message.id

            # Define paths
            day_folder = os.path.join(SAVE_PATH, str(year), month_name, f"{day:02}")
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

    # Save the last processed message ID for the month
    save_last_message_id(year, month, last_message_id)
    print(f"Finished scraping {year}-{month:02}, last message ID: {last_message_id}")

# Function to iterate over months and process messages
def process_messages():
    current_date = datetime.now(timezone.utc)
    year, month = START_DATE.year, START_DATE.month

    while True:
        process_month(year, month)

        # Stop if we reach the current month
        if year == current_date.year and month == current_date.month:
            break

        # Move to the next month
        month += 1
        if month > 12:
            month = 1
            year += 1

if __name__ == "__main__":
    print("Starting Telegram scraping...")
    process_messages()
    print("Telegram scraping completed successfully.")
