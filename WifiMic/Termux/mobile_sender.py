import pyaudio
import socket
import sys

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

def start_sender(pc_ip, port=5000):
    p = pyaudio.PyAudio()

    # Open stream
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error opening audio input: {e}")
        print("Make sure you have granted microphone permissions to Termux.")
        return

    # Initialize UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Streaming audio to {pc_ip}:{port}...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            sock.sendto(data, (pc_ip, port))
    except KeyboardInterrupt:
        print("\nStreaming stopped.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mobile_sender.py <PC_IP_ADDRESS>")
        sys.exit(1)
    
    pc_host = sys.argv[1]
    start_sender(pc_host)
