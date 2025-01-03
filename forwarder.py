import os
import requests
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DESTINATION_CHAT_ID = -1002167177194  # Your group ID

# Mapping of source groups/channels to destination topic IDs
GROUP_TO_TOPIC_MAPPING = {
    "@idf_telegram": 2,       # IDF -> Topic 2
    "@tzevaadomm": 3,         # Red Alerts -> Topic 3
    "@yediotnews10": 4,       # Israeli News -> Topic 4
    "@salehdesk1": 5,         # Arabs News -> Topic 5
}

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_updates(offset=None):
    """Fetch updates from Telegram"""
    url = f"{BASE_URL}/getUpdates"
    params = {"offset": offset, "timeout": 30}
    response = requests.get(url, params=params)
    return response.json()

def forward_message(chat_id, message_id, topic_id):
    """Forward a message to the destination chat"""
    url = f"{BASE_URL}/forwardMessage"
    data = {
        "chat_id": chat_id,
        "from_chat_id": chat_id,
        "message_id": message_id,
        "message_thread_id": topic_id,
    }
    response = requests.post(url, data=data)
    return response.json()

def main():
    print("Starting bot...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(offset=last_update_id)
            if updates.get("ok"):
                for update in updates.get("result", []):
                    last_update_id = update["update_id"] + 1
                    message = update.get("message")
                    if message and "chat" in message:
                        chat_username = message["chat"].get("username")
                        if chat_username in GROUP_TO_TOPIC_MAPPING:
                            topic_id = GROUP_TO_TOPIC_MAPPING[chat_username]
                            message_id = message["message_id"]

                            # Forward message
                            print(f"Forwarding message from {chat_username} to topic {topic_id}")
                            response = forward_message(DESTINATION_CHAT_ID, message_id, topic_id)
                            print("Response:", response)

            time.sleep(1)  # Avoid hitting rate limits
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
