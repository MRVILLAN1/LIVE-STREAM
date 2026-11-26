import os
import time
import threading
import subprocess
from pathlib import Path
from flask import Flask
import gdown

app = Flask(__name__)

VIDEO_DIR = Path("/app/videos")
PLAYLIST = Path("/app/playlist.txt")

DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
STREAM_KEY = os.environ.get("YOUTUBE_STREAM_KEY")

def start_stream():
    if not DRIVE_FOLDER_ID or not STREAM_KEY:
        print("ERROR: Drive folder ID or Stream Key missing")
        return

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading videos from Google Drive...")

    try:
        gdown.download_folder(
            id=DRIVE_FOLDER_ID,
            output=str(VIDEO_DIR),
            quiet=False,
            use_cookies=False,
            remaining_ok=True
        )
    except Exception as e:
        print("Drive download error:", e)
        return

    videos = sorted(VIDEO_DIR.rglob("*.mp4"))

    if not videos:
        print("No MP4 videos found!")
        return

    with open(PLAYLIST, "w", encoding="utf-8") as f:
        for video in videos:
            path = str(video.resolve())
            path = path.replace("\\", "\\\\").replace("'", "\\'")
            f.write(f"file '{path}'\n")

    print(f"Found {len(videos)} videos")

    command = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-fflags", "+genpts",
        "-f", "concat",
        "-safe", "0",
        "-i", str(PLAYLIST),
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1,format=yuv420p",
        "-af", "aresample=44100:async=1",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "2500k",
        "-maxrate", "2500k",
        "-bufsize", "5000k",
        "-g", "60",
        "-keyint_min", "60",
        "-sc_threshold", "0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "flv",
        f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    ]

    print("LIVE VERSION: v2 (re-encode 1280x720)")
    print("Starting YouTube LIVE...")

    subprocess.run(command)

@app.route("/")
def home():
    return "YouTube Live Service Running"

@app.route("/health")
def health():
    return "OK", 200

threading.Thread(target=start_stream, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
