import os
import subprocess
import json
import re
from flask import Flask, request, Response, send_file, render_template_string, redirect, url_for

app = Flask(__name__)

# --- CONFIGURATION ---
BASE_DIR = os.path.expanduser("~") # Home Directory

# --- HTML TEMPLATES ---

# 1. Directory Listing HTML
DIR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Network File Explorer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f4f4; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        ul { list-style: none; padding: 0; }
        li { padding: 10px; border-bottom: 1px solid #eee; display: flex; align-items: center; }
        li:last-child { border-bottom: none; }
        a { text-decoration: none; color: #333; font-weight: 500; flex-grow: 1; margin-left: 10px; }
        a:hover { color: #007bff; }
        .icon { font-size: 1.2em; }
        .btn-back { display: inline-block; margin-bottom: 15px; padding: 8px 15px; background: #ddd; color: #333; border-radius: 4px; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        {% if parent_path %}
        <a href="/?path={{ parent_path }}" class="btn-back">⬅ Back</a>
        {% endif %}
        <h2>📂 {{ current_folder_name }}</h2>
        <ul>
            {% for item in items %}
            <li>
                <span class="icon">{{ '📁' if item.is_dir else ('🎥' if item.is_video else '📄') }}</span>
                <a href="/handle?path={{ item.path }}">{{ item.name }}</a>
            </li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
"""

# 2. Video Player HTML (Custom Seeking Logic)
PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Stream: {{ filename }}</title>
    <style>
        body { background: #000; color: #fff; display: flex; flex-direction: column; align-items: center; justify_content: center; height: 100vh; margin: 0; font-family: sans-serif; }
        video { width: 90%; max-width: 1000px; max-height: 80vh; background: #222; }
        .controls { width: 90%; max-width: 1000px; margin-top: 10px; display: flex; gap: 10px; align-items: center; }
        /* Custom Range Slider for Seeking */
        input[type=range] { flex-grow: 1; cursor: pointer; }
        .time-display { font-variant-numeric: tabular-nums; }
        button { padding: 8px 15px; cursor: pointer; background: #007bff; border: none; color: white; border-radius: 4px; font-weight: bold; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h3>Playing: {{ filename }} (25 FPS)</h3>

    <!-- Video Element -->
    <video id="videoPlayer" autoplay>
        <source src="" type="video/mp4">
    </video>

    <!-- Custom Controls -->
    <div class="controls">
        <button id="playPauseBtn">⏯</button>
        <input type="range" id="seekBar" value="0" min="0" step="1">
        <span class="time-display"><span id="currentTime">00:00</span> / <span id="totalTime">00:00</span></span>
    </div>

    <script>
        const video = document.getElementById('videoPlayer');
        const seekBar = document.getElementById('seekBar');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const currentDisplay = document.getElementById('currentTime');
        const totalDisplay = document.getElementById('totalTime');

        // Server se aayi hui duration (seconds mein)
        const totalDuration = {{ duration }};
        const filePath = "{{ filepath }}";

        // Initial Setup
        seekBar.max = totalDuration;
        totalDisplay.innerText = formatTime(totalDuration);

        // Start playing from beginning
        loadVideoStream(0);

        // --- Functions ---

        function loadVideoStream(startTime) {
            // URL mein 't' parameter add karke seek request bhejo
            const streamUrl = `/stream_feed?path=${encodeURIComponent(filePath)}&t=${startTime}`;
            video.src = streamUrl;
            video.currentTime = 0; // Video element ka time reset karo kyunki naya stream shuru hua hai
            video.play();
        }

        function formatTime(seconds) {
            const m = Math.floor(seconds / 60);
            const s = Math.floor(seconds % 60);
            return `${m}:${s < 10 ? '0' : ''}${s}`;
        }

        // --- Event Listeners ---

        // 1. Play/Pause
        playPauseBtn.addEventListener('click', () => {
            if (video.paused) video.play();
            else video.pause();
        });

        // 2. Update Seekbar as video plays
        // Note: Hum 'real' time calculate karte hain: StartTime + VideoPlayTime
        let currentStreamStart = 0;

        video.addEventListener('timeupdate', () => {
            if (!video.seeking) {
                // Video ka current time + jahan se stream start hui thi
                const realTime = currentStreamStart + video.currentTime;
                seekBar.value = realTime;
                currentDisplay.innerText = formatTime(realTime);
            }
        });

        // 3. User ne Seek Bar hilaya (The Magic Part)
        seekBar.addEventListener('change', () => {
            const seekTo = seekBar.value;
            currentStreamStart = parseFloat(seekTo);
            console.log("Seeking to:", seekTo);

            // Nayi position se stream load karo
            loadVideoStream(seekTo);
        });

        // seekbar ko drag karte waqt time update ho lekin video load na ho
        seekBar.addEventListener('input', () => {
            currentDisplay.innerText = formatTime(seekBar.value);
        });

    </script>
</body>
</html>
"""

def get_video_duration(file_path):
    """ffprobe ka use karke video ki duration nikalta hai."""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        output = subprocess.check_output(cmd).decode().strip()
        return float(output)
    except:
        return 0

@app.route('/')
def index():
    """Directory Listing (HTML Output)."""
    req_path = request.args.get('path', BASE_DIR)

    # Security Check
    if not req_path.startswith(BASE_DIR):
        req_path = BASE_DIR

    items = []
    try:
        with os.scandir(req_path) as entries:
            for entry in entries:
                is_video = entry.name.lower().endswith(((".webm", ".mkv", ".flv", ".vob", ".ogv", ".ogg", ".rrc", ".gifv", ".mng", ".mov", ".avi", ".qt", ".wmv", ".yuv", ".rm", ".asf", ".amv", ".mp4", ".m4p", ".m4v", ".mpg", ".mp2", ".mpeg", ".mpe", ".mpv", ".m4v", ".svi", ".3gp", ".3g2", ".mxf", ".roq", ".nsv", ".flv", ".f4v", ".f4p", ".f4a", ".f4b", ".mod")))
                items.append({
                    'name': entry.name,
                    'path': entry.path,
                    'is_dir': entry.is_dir(),
                    'is_video': is_video
                })

        # Sort directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

        parent_path = os.path.dirname(req_path) if req_path != BASE_DIR else None

        return render_template_string(DIR_TEMPLATE,
                                      items=items,
                                      current_folder_name=os.path.basename(req_path) or "Home",
                                      parent_path=parent_path)
    except PermissionError:
        return "<h1>Access Denied</h1>"

@app.route('/handle')
def handle_file():
    """Decides whether to download file or open video player."""
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return "File not found", 404

    if os.path.isdir(path):
        return redirect(url_for('index', path=path))

    # Check for video
    video_exts = (".webm", ".mkv", ".flv", ".vob", ".ogv", ".ogg", ".rrc", ".gifv", ".mng", ".mov", ".avi", ".qt", ".wmv", ".yuv", ".rm", ".asf", ".amv", ".mp4", ".m4p", ".m4v", ".mpg", ".mp2", ".mpeg", ".mpe", ".mpv", ".m4v", ".svi", ".3gp", ".3g2", ".mxf", ".roq", ".nsv", ".flv", ".f4v", ".f4p", ".f4a", ".f4b", ".mod")
    if path.lower().endswith(video_exts):
        # Video Player Page par bhej do
        return video_player_page(path)
    else:
        # Normal file: Send Real Data
        return send_file(path)

def video_player_page(path):
    """Video ke liye HTML Player return karta hai."""
    duration = get_video_duration(path)
    filename = os.path.basename(path)
    # Template render karo path aur duration ke sath
    return render_template_string(PLAYER_TEMPLATE, filepath=path, duration=duration, filename=filename)

@app.route('/stream_feed')
def stream_feed():
    """Actual FFmpeg streaming endpoint."""
    file_path = request.args.get('path')
    start_time = request.args.get('t', '0') # Seek time

    if not file_path:
        return "No file specified", 400

    def generate():
        # FFmpeg Command
        cmd = [
            'ffmpeg',
            '-ss', start_time,          # Yahan se seek (jump) karega
            '-i', file_path,
            '-filter:v', 'fps=25',      # Requirement: 25 FPS
            '-c:v', 'libx264',
            '-preset', 'ultrafast',     # Realtime encoding speed
            '-tune', 'zerolatency',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-f', 'mp4',
            '-movflags', 'frag_keyframe+empty_moov', # Web Playback ke liye zaroori
            '-'
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**7
        )

        try:
            while True:
                data = process.stdout.read(4096)
                if not data:
                    break
                yield data
        finally:
            process.kill()

    return Response(generate(), mimetype='video/mp4')

if __name__ == '__main__':
    # Network par visible banane ke liye 0.0.0.0
    print("Server running on port 8000...")
    app.run(host='0.0.0.0', port=8000, threaded=True)
