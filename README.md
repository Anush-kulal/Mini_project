# Face Recognition Telegram Bot

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    > **Note**: If `dlib` fails to install, you may need to install **CMake** and **Visual Studio Build Tools** (with C++ support) first. Alternatively, look for a pre-compiled `.whl` file for `dlib` matching your Python version.

2.  **Configuration**:
    - Open `config.py`.
    - Add your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
    - Adjust cooldowns and thresholds if needed.

3.  **Register Your Face**:
    - Run the registration script:
      ```bash
      python register_face.py
      ```
    - Look at the camera and press `s` to save your face.
    - Press `q` to quit.

## Usage

Run the main system:
```bash
python main.py
```

- When your face is detected, it will send a greeting to Telegram.
- When an unknown face is detected, it will send an alert + photo to Telegram.
- Press `q` to stop the system.
