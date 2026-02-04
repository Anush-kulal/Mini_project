import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_message(text):
    """Sends a text message to the configured Telegram chat."""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN' or TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID':
        print("Error: Bot Token or Chat ID not set in config.py")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        return None

def send_photo(photo_path, caption=None):
    """Sends a photo to the configured Telegram chat."""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN' or TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID':
        print("Error: Bot Token or Chat ID not set in config.py")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": TELEGRAM_CHAT_ID}
    if caption:
        data["caption"] = caption
        
    try:
        with open(photo_path, "rb") as photo:
            files = {"photo": photo}
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()
    except FileNotFoundError:
        print(f"Error: Photo file not found at {photo_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error sending photo: {e}")
        return None
