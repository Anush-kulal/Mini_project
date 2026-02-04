# speech_to_text_whisper.py

import sounddevice as sd
import numpy as np
import whisper
import queue
import threading

SAMPLE_RATE = 16000
CHANNELS = 1

audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    audio_queue.put(indata.copy())

def start_whisper_stt(on_text_callback):
    """
    Fully free offline speech recognition using Whisper tiny/base/small model.
    on_text_callback(text) receives recognized text.
    """

    print("[Whisper STT] Loading Whisper model...")
    model = whisper.load_model("small")  # choose: tiny / base / small / medium / large
    print("[Whisper STT] Model loaded!")

    # Start microphone stream
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=audio_callback
    ):
        print("[Whisper STT] Listening... Speak!")

        audio_buffer = np.zeros((0, CHANNELS), dtype=np.float32)

        while True:
            data = audio_queue.get()
            audio_buffer = np.concatenate((audio_buffer, data), axis=0)

            # Transcribe every 4 seconds of audio
            if len(audio_buffer) >= SAMPLE_RATE * 4:
                audio_np = audio_buffer[:, 0]

                print("[Whisper STT] Transcribing...")
                result = model.transcribe(audio_np, fp16=False)
                text = result["text"].strip()

                if text:
                    print("[Whisper STT] Recognized:", text)
                    on_text_callback(text)

                # Reset buffer
                audio_buffer = np.zeros((0, CHANNELS), dtype=np.float32)
