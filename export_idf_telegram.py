from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import os
from datetime import datetime
import requests

# Telegram API credentials from environment variables
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHANNEL = "@idf_telegram"  # Replace with your channel username
START_DATE = datetime(2023, 10, 7)  # Starting from October 7, 2023
SAVE_PATH = "./IDFspokesman"

# Initialize Telegram client
client = TelegramClient('session', API_ID, API_HASH)

def download_media(media, folder_path, filename_prefix):
    """Download media (photos/videos) to the specified folder."""
    if isinstance(media, MessageMediaPhoto):
        filename = f"{filename_prefix}_photo.jpg"
        client.download_media(media, file=os.path.join(folder_path, filename))
        return filename
    elif isinstance(media, MessageMediaDocument):
        # Download videos or documents
        filename = f"{filename_prefix}_media.mp4" if 'video' in media.document.mime_type else f"{filename_prefix}_media"
        client.download_media(media, file=os.path.join(folder_path, filename))
        return filename
    return None

def process_messages():
    with client:
        for message in client.iter_messages(CHANNEL, offset_date=START_DATE, reverse=True):
            if not message.message and not message.media:
                continue

            # Extract date and message ID
            message_date = message.date.astimezone()
            year = message_date.year
            month = message_date.strftime("%B")
            day = message_date.day
            message_id = message.id

            # Define paths
            day_folder = os.path.join(SAVE_PATH, str(year), month, f"{day:02}")
            os.makedirs(day_folder, exist_ok=True)

            # Define Markdown file path
            md_filename = os.path.join(day_folder, f"{message_id}.md")
            media_folder = os.path.join(day_folder, str(message_id))

            # Process media
            media_links = []
            if message.media:
                os.makedirs(media_folder, exist_ok=True)
                media_filename = download_media(message.media, media_folder, f"{message_id}")
                if media_filename:
                    relative_media_path = os.path.relpath(os.path.join(media_folder, media_filename), day_folder)
                    media_links.append(relative_media_path)

            # Generate Markdown content
            md_content = f"## Message {message_id}\n\n"
            md_content += f"{message.message or ''}\n\n"

            # Add media links to Markdown
            for media in media_links:
                if media.endswith(".jpg"):
                    md_content += f"![Photo](./{media})\n"
                elif media.endswith(".mp4"):
                    md_content += f"![Video](./{media})\n"

            # Save Markdown file
            with open(md_filename, "w", encoding="utf-8") as md_file:
                md_file.write(md_content)
            print(f"Saved message {message_id} to {md_filename}")

if __name__ == "__main__":
    print("Starting Telegram scraping...")
    process_messages()
    print("Telegram scraping completed successfully.")
