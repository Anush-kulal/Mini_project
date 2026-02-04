import time
import threading
import queue
import sounddevice as sd
from piper.voice import PiperVoice
import os

# --- Configuration ---
# IMPORTANT: Replace this with the actual path to your downloaded Piper voice model
# You need the .onnx file and its corresponding .json config file in the same location.
VOICE_MODEL_PATH = "en_GB-semaine-medium.onnx" 

# --- Global Components ---
tts_queue = queue.Queue()

try:
    if not os.path.exists(VOICE_MODEL_PATH):
        print(f"Error: Voice model not found at '{VOICE_MODEL_PATH}'.")
        print("Please download the model files (.onnx and .json) and update the VOICE_MODEL_PATH variable.")
        # Raise an exception to prevent further execution without the model
        raise FileNotFoundError(f"Model file not found: {VOICE_MODEL_PATH}")

    # Load the voice model once
    voice = PiperVoice.load(VOICE_MODEL_PATH)
except Exception as e:
    print(f"Failed to load Piper voice model: {e}")
    # Use a dummy class to prevent crashes if the model fails to load
    class DummyVoice:
        def __init__(self):
            class DummyConfig:
                sample_rate = 22050
            self.config = DummyConfig()
        def synthesize(self, text):
            print(f"[TTS] (Dummy) Synthesizing: {text}")
            yield type('Chunk', (object,), {'audio_int16_array': b''})
    voice = DummyVoice()
    
# --- Worker Functions ---

def tts_worker():
    """
    Continuously reads text from the queue, synthesizes it using Piper, 
    and plays it through the sounddevice stream.
    """
    sample_rate = voice.config.sample_rate
    
    # Initialize the audio stream
    try:
        with sd.OutputStream(samplerate=sample_rate, dtype='int16', channels=1) as stream:
            print(f"[TTS Worker] Audio stream started (Sample Rate: {sample_rate} Hz).")
            while True:
                # Blocks until an item is available
                text = tts_queue.get()
                
                if text is None:
                    # Termination signal
                    print("[TTS Worker] Received shutdown signal. Exiting.")
                    break
                    
                print(f"[TTS] Speaking: \"{text}\"")
                
                # Synthesize and stream the audio data
                for chunk in voice.synthesize(text):
                    # The chunk.audio_int16_array contains raw PCM audio data
                    stream.write(chunk.audio_int16_array)
                    
                # Signal that the task is done, allowing the queue to track completion
                tts_queue.task_done()

    except Exception as e:
        print(f"[TTS Worker] An error occurred in the audio stream: {e}")
        tts_queue.task_done() # Ensure the queue isn't blocked on an error


def start_tts_server():
    """Start the TTS worker in a background thread"""
    # Create and start the thread
    thread = threading.Thread(target=tts_worker, daemon=True, name="TTS_Thread")
    thread.start()
    print("[TTS Server] Ready. Worker thread started.")
    return thread


# --- Main Execution ---
if __name__ == "__main__":
    tts_thread = start_tts_server()

    
    print("\n--- Sending test messages to the queue ---")
    
    # 1. Add a first message
    tts_queue.put("Hello, this is a test of the text to speech worker running in a separate thread.")
    
    # 2. Add a second message
    tts_queue.put("Piper is a fast and efficient neural text to speech system.")
    
    # 3. Add a third message
    tts_queue.put("The audio stream is handled by the sound device library.")
    
    # Wait until all items in the queue have been processed
    try:
        tts_queue.join()
        print("\n--- All messages processed ---")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    
    # Send the termination signal to the worker
    tts_queue.put(None)
    
    # Wait for the worker thread to finish its cleanup
    tts_thread.join(timeout=2)
    
    print("[TTS Server] Shutdown complete.")