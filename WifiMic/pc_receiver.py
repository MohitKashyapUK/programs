import pyaudio
import socket
import subprocess
import sys
import atexit

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
PORT = 5000

# Virtual Device Names
SINK_NAME = "WifiMicSink"
SOURCE_NAME = "WifiMicSource"

def setup_virtual_mic():
    print("Setting up virtual microphone...")
    # 1. Create a Null Sink
    subprocess.run([
        "pactl", "load-module", "module-null-sink", 
        f"sink_name={SINK_NAME}", 
        f"sink_properties=device.description={SINK_NAME}"
    ], check=True)
    
    # 2. Remap the monitor of that sink to a virtual source (microphone)
    subprocess.run([
        "pactl", "load-module", "module-remap-source",
        f"master={SINK_NAME}.monitor",
        f"source_name={SOURCE_NAME}",
        f"source_properties=device.description='Wireless_Microphone_Mobile'"
    ], check=True)
    
    print(f"Virtual Microphone '{SOURCE_NAME}' created successfully.")

def cleanup():
    print("\nCleaning up virtual devices...")
    subprocess.run(["pactl", "unload-module", "module-remap-source"], stderr=subprocess.DEVNULL)
    subprocess.run(["pactl", "unload-module", "module-null-sink"], stderr=subprocess.DEVNULL)

def get_default_gateway():
    try:
        # Run 'ip route show default' to find the gateway
        out = subprocess.check_output(["ip", "route", "show", "default"]).decode()
        # Typical output: 'default via 10.51.169.135 dev wlan0 ...'
        parts = out.split()
        if "via" in parts:
            idx = parts.index("via")
            return parts[idx + 1]
    except Exception as e:
        print(f"Could not auto-detect gateway: {e}")
    return None

def start_receiver(mobile_ip=None):
    if not mobile_ip:
        mobile_ip = get_default_gateway()
        if not mobile_ip:
            print("[ ERROR ] Could not find Mobile IP (Hotspot Gateway). Please provide it manually.")
            return
        print(f"[ AUTO ] Detected Mobile IP: {mobile_ip}")

    # Setup virtual mic
    try:
        setup_virtual_mic()
    except Exception as e:
        print(f"Warning: {e}")

    atexit.register(cleanup)
    p = pyaudio.PyAudio()

    # Find the index of our virtual sink
    target_index = None
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if SINK_NAME.lower() in dev['name'].lower():
            target_index = dev['index']
            break
    
    # If sink not found, use pulse/pipewire
    if target_index is None:
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if 'pulse' in dev['name'].lower() or 'pipewire' in dev['name'].lower():
                target_index = i
                break

    # Open playback stream
    stream = p.open(format=FORMAT,
                    channels=2, 
                    rate=RATE,
                    output=True,
                    output_device_index=target_index,
                    frames_per_buffer=CHUNK)

    # TCP Client: Connect to Mobile
    print(f"Connecting to mobile at {mobile_ip}:{PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0) # Timeout for connection
        sock.connect((mobile_ip, PORT))
        print("[ SUCCESS ] Connected to Mobile Mic!")
    except Exception as e:
        print(f"[ ERROR ] Could not connect: {e}")
        return

    # Force movement to WifiMicSink
    def force_route():
        import time
        for _ in range(10):
            time.sleep(0.5)
            try:
                inputs = subprocess.check_output(["pactl", "list", "sink-inputs"]).decode()
                current_id = None
                for line in inputs.splitlines():
                    line = line.strip()
                    if "Sink Input #" in line:
                        current_id = line.split("#")[-1].strip()
                    if current_id and "application.name = \"python" in line.lower():
                        subprocess.run(["pactl", "move-sink-input", current_id, SINK_NAME], check=True)
                        print(f"\n[ ROUTING ] Audio moved to {SINK_NAME}")
                        return
            except: continue

    import threading
    threading.Thread(target=force_route, daemon=True).start()

    try:
        while True:
            data = sock.recv(CHUNK * 2)
            if not data: break
            stereo_data = b''.join([data[i:i+2]*2 for i in range(0, len(data), 2)])
            stream.write(stereo_data)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sock.close()
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    start_receiver(target)
