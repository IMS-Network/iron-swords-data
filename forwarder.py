import asyncio
from telethon import TelegramClient, events
from telethon.errors import PersistentTimestampOutdatedError
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "user_forwarder_session")
DESTINATION_CHAT_ID = -1002167177194  # Your group ID

# Mapping of source groups/channels to destination topic IDs
GROUP_TO_TOPIC_MAPPING = {
    "@idf_telegram": 2,       # IDF -> Topic 2
    "@tzevaadomm": 3,         # Red Alerts -> Topic 3
    "@yediotnews10": 4,       # Israeli News -> Topic 4
    "@salehdesk1": 5,         # Arabs News -> Topic 5
}

# Create the Telegram client using your user account
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Function to forward messages to the correct topic
@client.on(events.NewMessage(chats=list(GROUP_TO_TOPIC_MAPPING.keys())))
async def forward_message(event):
    source_chat = event.chat.username or event.chat.id
    if source_chat in GROUP_TO_TOPIC_MAPPING:
        topic_id = GROUP_TO_TOPIC_MAPPING[source_chat]
        try:
            await client.forward_messages(
                entity=DESTINATION_CHAT_ID,
                messages=event.message,
                thread_id=topic_id,  # Forward to the specific topic
            )
            print(f"Message forwarded from {source_chat} to topic {topic_id}")
        except Exception as e:
            print(f"Failed to forward message from {source_chat} to topic {topic_id}: {e}")

# Function to keep the session alive and ensure synchronization
async def keep_alive():
    while True:
        try:
            # Small API call to ensure the session stays active
            await client.get_me()
            print("Session is active.")
        except PersistentTimestampOutdatedError:
            print("PersistentTimestampOutdatedError encountered. Reconnecting...")
            await client.disconnect()
            await client.connect()
        except Exception as e:
            print(f"Unexpected error during keep_alive: {e}")
        await asyncio.sleep(300)  # Run every 5 minutes

# Main function to start the client
async def main():
    try:
        print("Starting Telegram Forwarder...")
        await client.connect()

        # Check if connected
        if not await client.is_user_authorized():
            print("Please log in to Telegram using this script.")
            await client.start()

        print("Logged in as:", await client.get_me())
        
        # Run the keep-alive task alongside the main event loop
        await asyncio.gather(
            client.run_until_disconnected(),
            keep_alive(),
        )
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
