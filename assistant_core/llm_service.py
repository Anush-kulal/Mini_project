# llm_service.py
"""
LLM + convo + scheduling service.
Expose two functions:
  - on_authorized_user(user_id)   <-- starts greeting + conversation (non-blocking)
  - on_unknown_face(photo_bytes)  <-- saves/sends photo and alerts owner
"""

import os
import io
import sqlite3
import threading
import time
from datetime import datetime
import dateparser

# pip install pyttsx3 python-telegram-bot openai apscheduler opencv-python
import pyttsx3
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

# Optional: import openai if you will use OpenAI for the LLM
# import openai

# ========== CONFIG ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # if using OpenAI

DB_PATH = "assistant.db"
CAMERA_SAVE_DIR = "captured"
AUTHORIZED_USERS = {"alice": {"display": "Alice"}, "bob": {"display": "Bob"}}

# ========== INIT ==========
os.makedirs(CAMERA_SAVE_DIR, exist_ok=True)
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 150)

scheduler = BackgroundScheduler()
scheduler.start()

# ========== DB ==========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        title TEXT,
        notes TEXT,
        when_ts INTEGER,
        notified INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def add_schedule(user_id, title, notes, when_ts):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO schedules (user_id, title, notes, when_ts) VALUES (?, ?, ?, ?)",
                (user_id, title, notes, int(when_ts)))
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid

def mark_notified(schedule_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE schedules SET notified = 1 WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()

def get_user_upcoming(user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT title, notes, when_ts FROM schedules WHERE user_id = ? ORDER BY when_ts LIMIT ?",
                (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

# ========== TTS & simple STT hook ==========
def speak(text):
    """Blocking TTS call. Swap with better TTS if you want."""
    print("[TTS]", text)
    tts_engine.say(text)
    tts_engine.runAndWait()

def transcribe_audio_from_mic_demo():
    """Placeholder STT for demo: developer types text.
       Replace this with your real STT implementation (whisper/vosk/etc)."""
    print("Simulated STT: type what the user said (or Enter for none):")
    txt = input("> ").strip()
    return txt

# ========== LLM / NLU (simple) ==========
def reply_with_llm_sim(user_text, user_id):
    """Simple echo fallback. Replace with real LLM call (OpenAI or local)"""
    # Example: call OpenAI here if you wish
    # openai.api_key = OPENAI_API_KEY
    # resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[...])
    return f"I heard: {user_text}"

def parse_intent_simple(text):
    t = (text or "").lower()
    if "remind me" in t or "schedule" in t or "add" in t:
        return "add_schedule"
    if "show schedule" in t or "what's my schedule" in t or "my schedule" in t:
        return "show_schedule"
    return "chat"

def extract_datetime_from_text(text):
    return dateparser.parse(text)

# ========== Notifications & unknown face handling ==========
def send_photo_to_owner(photo_bytes_io, caption="Unknown person detected"):
    if not telegram_bot:
        print("Telegram bot not configured; cannot send photo.")
        return False
    photo_bytes_io.seek(0)
    telegram_bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo_bytes_io, caption=caption)
    return True

def on_unknown_face(photo_bytes_io):
    """Save locally and notify owner (Telegram). This runs synchronously; caller may start a thread."""
    ts = int(time.time())
    filename = os.path.join(CAMERA_SAVE_DIR, f"unknown_{ts}.jpg")
    with open(filename, "wb") as f:
        f.write(photo_bytes_io.getbuffer())
    print("Saved unknown face photo to", filename)
    try:
        sent = send_photo_to_owner(photo_bytes_io, caption=f"Unknown person seen at {datetime.now().isoformat()}")
        if sent:
            speak("I detected someone I don't recognize — the owner has been notified.")
        else:
            speak("I detected an unknown person but couldn't notify the owner.")
    except Exception as e:
        print("Error while notifying owner:", e)
        speak("Failed to send the unknown-person photo due to an error.")

# ========== Reminder trigger ==========
def trigger_notification(schedule_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, title, notes, when_ts FROM schedules WHERE id = ?", (schedule_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return
    user_id, title, notes, when_ts = row
    when_str = datetime.fromtimestamp(when_ts).strftime("%Y-%m-%d %H:%M")
    msg = f"Reminder for {AUTHORIZED_USERS.get(user_id, {}).get('display', user_id)}: {title} at {when_str}. {notes}"
    speak(msg)
    # optional external notify:
    try:
        if telegram_bot:
            telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"[Reminder] {msg}")
    except Exception as e:
        print("Failed to send reminder externally:", e)
    mark_notified(schedule_id)

# Periodic safety polling in case scheduled jobs were missed
def poll_pending_schedules():
    now_ts = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM schedules WHERE when_ts <= ? AND notified = 0", (now_ts,))
    rows = cur.fetchall()
    conn.close()
    for r in rows:
        scheduler.add_job(trigger_notification, args=[r[0]])

# schedule the poll job
scheduler.add_job(poll_pending_schedules, "interval", seconds=60, id="poll_pending", replace_existing=True)

# ========== Conversation session (authorized user) ==========
def conversation_session(user_id, session_timeout=90):
    """Blocking conversation session. Meant to be run in a thread."""
    display = AUTHORIZED_USERS.get(user_id, {}).get("display", user_id)
    speak(f"Hi {display}, nice to see you. How can I help?")
    start_time = time.time()
    while time.time() - start_time < session_timeout:
        text = transcribe_audio_from_mic_demo()  # replace with real STT
        if not text:
            break
        intent = parse_intent_simple(text)
        if intent == "add_schedule":
            dt = extract_datetime_from_text(text)
            if not dt:
                speak("When should I remind you? Please say a date and time.")
                follow = transcribe_audio_from_mic_demo()
                dt = extract_datetime_from_text(follow)
            if dt:
                title = text  # naive: keep original text as title
                sid = add_schedule(user_id, title, "", int(dt.timestamp()))
                # schedule the job
                scheduler.add_job(trigger_notification, 'date', run_date=dt, args=[sid], id=f"reminder-{sid}")
                speak(f"Okay — scheduled: {title} at {dt.strftime('%Y-%m-%d %H:%M')}")
            else:
                speak("I couldn't understand the time.")
        elif intent == "show_schedule":
            rows = get_user_upcoming(user_id)
            if not rows:
                speak("You have no upcoming schedules.")
            else:
                speak("Here are your upcoming items:")
                for title, notes, when_ts in rows:
                    when = datetime.fromtimestamp(when_ts).strftime("%Y-%m-%d %H:%M")
                    speak(f"{title} at {when}")
        else:
            # normal chat via LLM or simple reply
            reply = reply_with_llm_sim(text, user_id)
            speak(reply)

# ========== Public functions used by face runner ==========
def on_authorized_user(user_id):
    """Call when face recognition returns a known user label."""
    # run session in a separate thread so face loop isn't blocked
    t = threading.Thread(target=conversation_session, args=(user_id,), daemon=True)
    t.start()

def on_unknown_face_and_notify(photo_bytes_io):
    """Call when face recognition returned unknown; photo_bytes_io is io.BytesIO"""
    t = threading.Thread(target=on_unknown_face, args=(photo_bytes_io,), daemon=True)
    t.start()

# initialize DB on import
init_db()
