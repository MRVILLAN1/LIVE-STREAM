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
        print("ERROR: Drive folder ID or Stream Key missing", flush=True)
        return

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading videos from Google Drive...", flush=True)

    try:
        gdown.download_folder(
            id=DRIVE_FOLDER_ID,
            output=str(VIDEO_DIR),
            quiet=False,
            use_cookies=False,
            remaining_ok=True
        )
    except Exception as e:
        print("Drive download error:", e, flush=True)
        return

    videos = sorted(VIDEO_DIR.rglob("*.mp4"))

    if not videos:
        print("No MP4 videos found!", flush=True)
        return

    with open(PLAYLIST, "w", encoding="utf-8") as f:
        for video in videos:
            path = str(video.resolve())
            path = path.replace("\\", "\\\\").replace("'", "\\'")
            f.write(f"file '{path}'\n")

    print(f"Found {len(videos)} videos", flush=True)

    command = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-fflags", "+genpts",
        "-f", "concat",
        "-safe", "0",
        "-i", str(PLAYLIST),
        "-vf", "scale=640:360:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=640:360:(ow-iw)/2:(oh-ih)/2,fps=24,setsar=1,format=yuv420p",
        "-af", "aresample=44100:async=1",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-b:v", "900k",
        "-maxrate", "900k",
        "-bufsize", "1800k",
        "-g", "48",
        "-keyint_min", "48",
        "-sc_threshold", "0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "flv",
        f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    ]

    while True:
        print("LIVE VERSION: v4 (re-encode 640x360 ultrafast)", flush=True)
        print("Starting YouTube LIVE...", flush=True)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(line.replace(STREAM_KEY, "***"), end="", flush=True)

        process.wait()
        print("ffmpeg stopped, restarting in 10 seconds...", flush=True)
        time.sleep(10)

@app.route("/")
def home():
    return "YouTube Live Service Running"

@app.route("/health")
def health():
    return "OK", 200

threading.Thread(target=start_stream, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
