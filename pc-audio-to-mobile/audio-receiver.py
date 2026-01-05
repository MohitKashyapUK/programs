import pyaudio
import socket
import opuslib

# --- Config (Must match Server) ---
CHANNELS = 2
RATE = 48000
CHUNK = 960
MAX_PACKET_SIZE = 4096

audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16, channels=CHANNELS, rate=RATE, output=True)
decoder = opuslib.Decoder(RATE, CHANNELS)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 12345))

print("Listening...")

try:
    while True:
        try:
            encoded_data, addr = sock.recvfrom(MAX_PACKET_SIZE)

            # Decode attempt
            decoded_data = decoder.decode(encoded_data, CHUNK)
            stream.write(decoded_data)

        except opuslib.OpusError:
            # Agar koi packet corrupt hai, to "Error" print karke agle packet ka wait karein
            # print(".", end="", flush=True) # Debugging ke liye dot print karein
            pass

except KeyboardInterrupt:
    stream.stop_stream()
    stream.close()
    audio.terminate()
