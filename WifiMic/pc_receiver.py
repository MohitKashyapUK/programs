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

def start_receiver():
    # Setup virtual mic
    try:
        setup_virtual_mic()
    except Exception as e:
        print(f"Warning: Failed to setup virtual mic automatically: {e}")
        print("You might need to install 'pulseaudio-utils' or 'libpulse'.")

    atexit.register(cleanup)

    p = pyaudio.PyAudio()

    # Find the index of our virtual sink or pulse/pipewire wrapper
    target_index = None
    print("\n--- Available Audio Devices ---")
    devices = []
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        devices.append(dev)
        print(f"Index {i}: {dev['name']}")

    # Priority 1: The actual Sink
    for dev in devices:
        if SINK_NAME.lower() in dev['name'].lower():
            target_index = dev['index']
            print(f"-> Found Specific Sink: {dev['name']}")
            break
    
    # Priority 2: Pulse/Pipewire
    if target_index is None:
        for dev in devices:
            name = dev['name'].lower()
            if 'pulse' in name or 'pipewire' in name:
                target_index = dev['index']
                print(f"-> Using Sound Server: {dev['name']}")
                break

    # Open stream
    stream = p.open(format=FORMAT,
                    channels=2, 
                    rate=RATE,
                    output=True,
                    output_device_index=target_index,
                    frames_per_buffer=CHUNK)

    # Initialize UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    sock.bind(("0.0.0.0", PORT))
    
    print(f"\n--- RECEIVER ACTIVE ---")
    print(f"IP Address: 10.51.169.128")
    print("-----------------------\n")

    # Force movement to WifiMicSink
    def force_route():
        import time
        print("[ ROUTING ] Searching for audio stream...")
        for _ in range(15): # Try for 7.5 seconds
            time.sleep(0.5)
            try:
                # Get detailed list of all sink-inputs
                inputs = subprocess.check_output(["pactl", "list", "sink-inputs"]).decode()
                
                current_id = None
                lines = inputs.splitlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if "Sink Input #" in line:
                        current_id = line.split("#")[-1].strip()
                    
                    # Look for Python or ALSA Playback related to this script
                    if current_id and ("application.name = \"python" in line.lower() or "ALSA Playback" in line):
                        # Move it to our sink
                        subprocess.run(["pactl", "move-sink-input", current_id, SINK_NAME], check=True)
                        print(f"\n[ SUCCESS ] Moved Python stream {current_id} to {SINK_NAME}")
                        return # Mission accomplished
            except Exception:
                continue
        print("\n[ WARNING ] Could not auto-route. Please move it manually in Sound Settings.")

    import threading
    threading.Thread(target=force_route, daemon=True).start()

    packet_count = 0
    try:
        while True:
            try:
                data, addr = sock.recvfrom(CHUNK * 4) 
                stereo_data = b''.join([data[i:i+2]*2 for i in range(0, len(data), 2)])
                stream.write(stereo_data)
                
                packet_count += 1
                if packet_count % 50 == 0:
                    print(f"\r[ ACTIVE ] Incoming: {packet_count} packets", end="")
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\nStopping receiver.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        sock.close()

if __name__ == "__main__":
    start_receiver()
