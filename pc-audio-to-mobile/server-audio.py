import pyaudio
import socket
import opuslib
import subprocess
import pulsectl
import time
import os

# --- Function: Gateway IP (.213) nikalne ke liye ---
def get_default_gateway():
    try:
        result = subprocess.check_output(["ip", "route", "show", "default"]).decode("utf-8")
        if "via" in result:
            ip_part = result.split("via")[1].strip().split(" ")[0]
            return ip_part
        else:
            return None
    except Exception as e:
        print(f"Error finding gateway: {e}")
        return None

# --- Function: Stream ko zabardasti Monitor Source par move karna ---
def move_stream_to_monitor():
    """
    Ye function wahi kaam karta hai jo aap Pavucontrol mein karte hain.
    Ye chal rahe recording stream ko dhoondhta hai aur usse 'Monitor' par shift kar deta hai.
    """
    print("🔄 Moving audio source to System Monitor (Loopback)...")
    try:
        with pulsectl.Pulse('python-audio-mover') as pulse:
            # 1. Default Speaker ka Monitor source dhoondho
            server_info = pulse.server_info()
            default_sink_name = server_info.default_sink_name
            sink = pulse.get_sink_by_name(default_sink_name)
            monitor_source_name = sink.monitor_source_name
            
            # Monitor source ka object nikalo taaki index mil sake
            target_source = pulse.get_source_by_name(monitor_source_name)
            
            print(f"🎯 Target Source: {monitor_source_name}")

            # 2. Hamari Python script ki recording stream dhoondho
            # Hum thoda wait karte hain taaki PyAudio stream bana chuka ho
            time.sleep(1) 
            
            found = False
            for source_output in pulse.source_output_list():
                # Check karte hain ki ye stream hamari script ki hai ya nahi
                # PyAudio aksar "python" ya "ALSA plug-in" naam se aata hai
                try:
                    props = source_output.proplist
                    # Agar process ID match kare ya naam mein python ho
                    if 'python' in props.get('application.name', '').lower() or \
                       'python' in props.get('application.process.binary', '').lower() or \
                       'ALSA plug-in [python' in source_output.name:
                        
                        # Step 3: Stream ko move karo
                        pulse.source_output_move(source_output.index, target_source.index)
                        print(f"✅ Success! Stream moved to: {monitor_source_name}")
                        found = True
                        break
                except Exception as e:
                    continue
            
            if not found:
                print("⚠️ Warning: Python recording stream nahi mili. Pavucontrol check karein.")

    except Exception as e:
        print(f"❌ Error moving stream: {e}")

GATEWAY_IP = get_default_gateway()

if GATEWAY_IP:
    print(f"✅ Gateway IP Detected: {GATEWAY_IP}")
    print(f"Targeting: {GATEWAY_IP}")
else:
    print("❌ Gateway IP nahi mili! Check connection.")
    exit()

# --- Configuration ---
CLIENT_IP = GATEWAY_IP
PORT = 12345

# Audio Config
CHANNELS = 2
RATE = 48000
CHUNK = 960

# --- Audio Setup ---
audio = pyaudio.PyAudio()

print("🎤 Starting Audio Stream on Default Device first...")

# Hum yahan device_index nahi denge, system default uthayenge
stream = audio.open(format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

# --- Encoder Setup ---
encoder = opuslib.Encoder(RATE, CHANNELS, 'voip')
encoder.bitrate = 32000

# --- Network Start ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- MAGIC: Ab stream start hone ke baad usse move karenge ---
move_stream_to_monitor()

print(f"📡 Streaming started to {CLIENT_IP}:{PORT}")

try:
    while True:
        try:
            raw_data = stream.read(CHUNK, exception_on_overflow=False)

            if len(raw_data) != CHUNK * CHANNELS * 2:
                continue

            encoded_data = encoder.encode(raw_data, CHUNK)
            sock.sendto(encoded_data, (CLIENT_IP, PORT))

        except Exception:
            pass

except KeyboardInterrupt:
    print("\nStopping...")
    stream.stop_stream()
    stream.close()
    audio.terminate()
    sock.close()
