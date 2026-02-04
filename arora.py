# main.py
from google import genai
from speech1 import start_tts_server, tts_queue

import speech_recognition as sr
import os
import sqlite3
from datetime import datetime
# Get API key from environment variable or use the one below
# Set it in your environment: $env:GEMINI_API_KEY = "your-api-key-here"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB9XpQEordnKtcTCDN_FD4RICd9YXijSfo")

# -----------------------------
#  MICROPHONE SELECTION
# -----------------------------
def list_microphones():
    """List all available microphones and input options"""
    print("\n" + "="*60)
    print("Available Input Options:")
    print("="*60)
    mic_list = sr.Microphone.list_microphone_names()
    for i, mic_name in enumerate(mic_list):
        print(f"  [{i}] {mic_name}")
    # Add text input as an option
    text_option_index = len(mic_list)
    print(f"  [{text_option_index}] Text Input (Type messages)")
    print("="*60)
    return mic_list

def select_microphone():
    """Allow user to select a microphone or text input"""
    print("\n" + "="*60)
    print("Microphone Selection")
    print("="*60)
    print("[0] Use Default Microphone")
    print("[1] Use Text Input")
    print("="*60)
    
    while True:
        try:
            choice = input("\nSelect option (0 or 1) or press Enter for default microphone: ").strip()
            
            if choice == "":
                print("[INFO] Using default microphone.")
                return None
            
            option = int(choice)
            if option == 0:
                print("[INFO] Using default microphone.")
                return None
            elif option == 1:
                print("[INFO] Selected text input mode.")
                return "text"
            else:
                print("[ERROR] Please enter 0 or 1")
        except ValueError:
            print("[ERROR] Please enter a valid number or press Enter for default.")
        except KeyboardInterrupt:
            print("\n[INFO] Using default microphone.")
            return None

# -----------------------------
#  TEXT INPUT
# -----------------------------
def get_text_input():
    """Get text input from user"""
    try:
        user_input = input("\n[TEXT] Type your message (or press Enter to skip): ").strip()
        if user_input:
            print(f"[TEXT] You typed: {user_input}")
            return user_input
        return None
    except (EOFError, KeyboardInterrupt):
        return None

# -----------------------------
#  SPEECH-RECOGNITION (recognize_google backend)
# -----------------------------
def listen_once(duration=3, mic_index=None):
    """
    Record from the default microphone (or mic_index) and return recognized text.
    Uses the SpeechRecognition library with Google's free web API (recognize_google).
    duration: max seconds to record (phrase_time_limit)
    mic_index: optional device index for Microphone(device_index=mic_index)
    """
    r = sr.Recognizer()

    # Use the selected microphone (None -> default)
    mic_args = {}
   

    with sr.Microphone(**mic_args) as source:
        # adjust for ambient noise briefly
        print("Adjusting for ambient noise... (0.5s)")
        r.adjust_for_ambient_noise(source, duration=0.5)
        print(f"[MIC] Listening for up to {duration} seconds... Say something!")
        try:
            # phrase_time_limit controls maximum listen length; timeout waits for phrase to start
            audio = r.listen(source, timeout=5, phrase_time_limit=duration)
        except sr.WaitTimeoutError:
            print("[TIMEOUT] No speech detected (timeout).")
            return ""

    # Try to recognize using Google Web Speech API (free, limited)
    try:
        text = r.recognize_google(audio)
        print("[RECOGNIZED] You said:", text)
        return text
    except sr.UnknownValueError:
        print("[ERROR] Could not understand audio.")
        return ""
    except sr.RequestError as e:
        print(f"[ERROR] API request failed: {e}")
        return ""

# -----------------------------
#  TTS + GEMINI integration
# -----------------------------
def main():
    # Initialize database
    init_database()
    
    # start TTS worker (from your speech1 module)
    tts_thread = start_tts_server()
    
    selected_mic = None
    input_mode = 'both'  # Listen to both voice and text simultaneously

    # initialize Gemini client with API key
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Please set it as an environment variable or in the code.")
    
    # Validate API key format (should start with AIza)
    if not GEMINI_API_KEY.startswith("AIza"):
        print(f"[WARNING] API key format looks incorrect. Expected format: AIza...")
    
    print(f"[DEBUG] Initializing Gemini client with API key (length: {len(GEMINI_API_KEY)})")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("[DEBUG] Client initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        raise
    
    # Debug: Check available methods (uncomment to debug)
    # print(f"[DEBUG] Client type: {type(client)}")
    # print(f"[DEBUG] Client methods: {[m for m in dir(client) if not m.startswith('_')]}")
    # if hasattr(client, 'models'):
    #     print(f"[DEBUG] Models type: {type(client.models)}")
    #     print(f"[DEBUG] Models methods: {[m for m in dir(client.models) if not m.startswith('_')]}")
    
    print("[ASSISTANT] Voice assistant started.")
    print("[INFO] Listening for voice input and accepting text input simultaneously.")
    print("[INFO] Say 'exit' or type 'exit' to quit.\n")
    
    # Greet the user
    greeting = "Hello sir, how can I help you today?"
    print("[GREETING]", greeting)
    tts_queue.put(greeting)
    tts_queue.join()
    
    # Keep conversation history for context
    conversation_history = []
    
    import threading
    
    while True:
        user_text = None
        
        # Use threading to listen for voice and text input simultaneously
        voice_input = [None]
        text_input = [None]
        
        def get_voice():
            voice_input[0] = listen_once(duration=3, mic_index=selected_mic)
        
        def get_text():
            text_input[0] = get_text_input()
        
        # Start both threads
        voice_thread = threading.Thread(target=get_voice, daemon=True)
        text_thread = threading.Thread(target=get_text, daemon=True)
        
        voice_thread.start()
        text_thread.start()
        
        # Wait for either input to arrive (whichever comes first)
        voice_thread.join(timeout=0.1)
        text_thread.join(timeout=0.1)
        
        # Prioritize text input if both are available, otherwise use voice
        if text_input[0]:
            user_text = text_input[0]
            print("[TEXT INPUT]", user_text)
        elif voice_input[0]:
            user_text = voice_input[0]
        else:
            # Wait a bit longer for voice input
            voice_thread.join(timeout=5)
            if voice_input[0]:
                user_text = voice_input[0]
            elif text_input[0]:
                user_text = text_input[0]
            else:
                print("No input detected. Continuing to listen...")
                continue
        
        # Check for mode switching commands
        user_lower = user_text.lower().strip()
        if "switch to text" in user_lower or "text mode" in user_lower or "use text" in user_lower:
            print("[INFO] Already accepting both text and voice input.")
            continue
        elif "switch to voice" in user_lower or "voice mode" in user_lower or "use voice" in user_lower:
            print("[INFO] Already accepting both text and voice input.")
            continue
        
        # Check if user wants to schedule
        if sheduler(user_text, mic_index=selected_mic):
            continue  # Continue listening after scheduling
        
        # Check if user is asking about schedules
        user_lower = user_text.lower().strip()
        schedule_keywords = ["schedule", "schedules", "tasks", "task", "what do i have", "what's scheduled", 
                           "show me my schedule", "tell me my schedule", "what are my tasks"]
        
        if any(keyword in user_lower for keyword in schedule_keywords):
            tasks = get_schedules(status='pending')
            if tasks:
                reply_text = "Here are your scheduled tasks: "
                task_list = []
                for i, (task_id, task_text, created_at, status) in enumerate(tasks, 1):
                    task_list.append(f"Task {i}: {task_text}")
                    reply_text += f"Task {i}: {task_text}. "
            else:
                reply_text = "You have no scheduled tasks."
            
            print("[SCHEDULES]", reply_text)
            tts_queue.put(reply_text)
            tts_queue.join()
            
            # Add to conversation history
            conversation_history.append({
                "role": "user",
                "parts": [user_text]
            })
            conversation_history.append({
                "role": "model",
                "parts": [reply_text]
            })
            continue
        
        # Check if user wants to exit
        if user_text.lower().strip() in ["exit", "quit", "stop", "goodbye"]:
            print("[EXIT] Exiting voice assistant...")
            tts_queue.put("Goodbye! It was nice talking to you.")
            tts_queue.join()  # Wait for goodbye message to finish
            break

        # Add user message to conversation history
        conversation_history.append({
            "role": "user",
            "parts": [user_text]
        })

        # send conversation history to Gemini LLM for context-aware responses
        try:
            # Try multiple API call formats to find the correct one
            response = None
            last_error = None
            
            # Method 1: client.models.generate_content() with conversation history
            if not response:
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=conversation_history
                    )
                except Exception as e1:
                    last_error = e1
                    # Method 2: Try without .models
                    try:
                        response = client.generate_content(
                            model="gemini-2.5-flash",
                            contents=conversation_history
                        )
                    except Exception as e2:
                        last_error = e2
                        # Method 3: Try with just the current message as string
                        try:
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=user_text
                            )
                        except Exception as e3:
                            last_error = e3
                            raise last_error
            
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] Error calling Gemini: {type(e).__name__}: {e}")
            
            # Check for specific API key errors
            if "API Key" in error_msg or "API_KEY" in error_msg or "INVALID_ARGUMENT" in error_msg:
                print("\n[ERROR] API Key issue detected!")
                print("Please get a valid API key from: https://aistudio.google.com/apikey")
                print("Then set it as an environment variable: $env:GEMINI_API_KEY = 'your-api-key'")
                print("Or update the GEMINI_API_KEY variable in this file.\n")
            
            # import traceback
            # traceback.print_exc()  # Print full traceback for debugging
            # fallback: echo
            reply_text = "Sorry, I could not reach the language model. You said: " + user_text
        else:
            # clean the LLM output by removing asterisks (markdown bold/italic markers)
            # Some SDKs return .text; others may return dict — handle common cases:
            if hasattr(response, "text"):
                raw = response.text
            elif isinstance(response, dict) and "output" in response:
                raw = response["output"]
            else:
                raw = str(response)
            reply_text = raw.replace("*", "")

        # Add assistant response to conversation history
        conversation_history.append({
            "role": "model",
            "parts": [reply_text]
        })

        print("[Reply]", reply_text)

        # enqueue the cleaned reply for TTS playback
        tts_queue.put(reply_text)
        
        # Wait for TTS to finish before listening again
        tts_queue.join()

    # signal TTS worker to stop and wait briefly
    tts_queue.put(None)
    tts_thread.join(timeout=2)
    print("[DONE] Voice assistant stopped.")

def init_database():
    """Initialize the schedule database and create table if it doesn't exist"""
    db_path = os.path.join(os.path.dirname(__file__), "schedule.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at: {db_path}")

def store_data(text):
    """Store scheduled task data in schedule.db"""
    if not text or not text.strip():
        print("[STORE] Empty task, not storing.")
        return False
    
    db_path = os.path.join(os.path.dirname(__file__), "schedule.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Insert the task
        cursor.execute('''
            INSERT INTO schedules (task_text, created_at, status)
            VALUES (?, ?, ?)
        ''', (text.strip(), datetime.now().isoformat(), 'pending'))
        
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        
        print(f"[STORE] Task stored successfully (ID: {task_id}): {text.strip()}")
        return True
    except Exception as e:
        print(f"[STORE] Error storing task: {e}")
        return False

def get_schedules(status='pending'):
    """Retrieve scheduled tasks from database"""
    db_path = os.path.join(os.path.dirname(__file__), "schedule.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT id, task_text, created_at, status 
                FROM schedules 
                WHERE status = ?
                ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT id, task_text, created_at, status 
                FROM schedules 
                ORDER BY created_at DESC
            ''')
        
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    except Exception as e:
        print(f"[DB] Error retrieving schedules: {e}")
        return []

def sheduler(user_text, mic_index=None):
    """Handle scheduling requests"""
    if user_text.lower() == "schedule" or user_text.lower() == "shedule":
        print("[SCHEDULER] Scheduling a task...")
        tts_queue.put("Scheduling a task...")
        tts_queue.join()
        
        # Get task from voice or text input
        task_text = listen_once(duration=6, mic_index=mic_index)
        if not task_text:
            task_text = get_text_input()
        
        if task_text:
            store_data(task_text) 
            tts_queue.put("Task scheduled successfully.")
            tts_queue.join()    
            return True
        else:
            tts_queue.put("I'm sorry, I didn't understand that. Please try again.")
            tts_queue.join()
            return False
    return False
        
if __name__ == "__main__":
    main()