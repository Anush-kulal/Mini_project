import os

# Telegram Bot Configuration
# Replace 'YOUR_BOT_TOKEN' and 'YOUR_CHAT_ID' with your actual values if not using environment variables.
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8227336417:AAFsfFdP9Wz74skeTWYv_JxUEUJbDXDi-Yw')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '2129202778')

# Face Recognition Configuration
KNOWN_FACES_DIR = "known_faces"
UNKNOWN_FACES_DIR = "unknown_faces"

# Create directories if they don't exist
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)

# Application Settings
MATCH_THRESHOLD = 0.5  # Lower is stricter
GREETING_COOLDOWN = 60 * 60  # Seconds (e.g., once per hour)
UNKNOWN_ALERT_COOLDOWN = 3 # Seconds (e.g., once every 3 second)
