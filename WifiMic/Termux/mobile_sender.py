import pyaudio
import socket
import sys

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
PORT = 5000

def start_mobile_server():
    p = pyaudio.PyAudio()

    # Open microphone stream
    try:
        mic_stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Create TCP Server (Better for firewall bypass in this mode)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", PORT))
    server_sock.listen(1)

    print(f"\n--- MOBILE SERVER READY ---")
    # Get local IP for display
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Mobile IP: (Check Android Wifi Settings)")
    print(f"Listening on port: {PORT}")
    print("----------------------------\n")

    while True:
        print("Waiting for PC to connect...")
        conn, addr = server_sock.accept()
        print(f"PC Connected from {addr[0]}")
        
        try:
            while True:
                data = mic_stream.read(CHUNK, exception_on_overflow=False)
                conn.sendall(data)
        except (ConnectionResetError, BrokenPipeError):
            print("PC Disconnected.")
        except KeyboardInterrupt:
            break
        finally:
            conn.close()

    mic_stream.stop_stream()
    mic_stream.close()
    p.terminate()

if __name__ == "__main__":
    start_mobile_server()
