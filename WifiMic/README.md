# WifiMic: Android to Arch Linux Wireless Microphone

Transform your Android phone into a high-quality wireless microphone for your Arch Linux PC. This project uses **UDP** for low-latency audio streaming and **PipeWire/PulseAudio** to create a virtual input device that works in Discord, Zoom, OBS, and more.

---

## 🚀 How it Works

1.  **Mobile Side**: The `mobile_sender.py` script (running in Termux) captures audio from your phone's microphone and sends it as raw PCM data packets over UDP to your PC's IP address.
2.  **PC Side**: The `pc_receiver.py` script listens on port `5000`. 
    *   It creates a **Virtual Sink** (`WifiMicSink`) which acts like a "silent speaker".
    *   It creates a **Virtual Source** (`Wireless_Microphone_Mobile`) which "listens" to that silent speaker and acts as a microphone.
    *   The script automatically routes the incoming audio into this virtual device so you don't hear your own voice through your PC speakers.

---

## 🛠️ Arch Linux Setup (PC)

### 1. Install Dependencies
You need Python, PyAudio, and PulseAudio utilities (even if you use PipeWire).
```bash
sudo pacman -S python python-pyaudio libpulse
```

### 2. Configure Firewall
Arch Linux often blocks incoming UDP packets. You must allow port `5000` or temporarily disable the firewall:
```bash
# To allow the port
sudo ufw allow 5000/udp

# To temporarily disable (if audio isn't reaching)
sudo ufw disable
```

### 3. Run the Receiver
```bash
cd WifiMic
python pc_receiver.py
```
*Wait for the script to show `[ SUCCESS ] Moved Python stream...` after you start the mobile sender.*

---

## 📱 Termux Setup (Mobile)

### 1. Install Termux
Install Termux from F-Droid (Play Store version is outdated).

### 2. Install Dependencies
Run these commands inside Termux:
```bash
pkg update && pkg upgrade
pkg install python portaudio clang
pip install pyaudio
```

### 3. Grant Permissions
Go to your **Android Settings > Apps > Termux > Permissions** and ensure **Microphone** is enabled.

### 4. Run the Sender
Find your PC's local IP (usually starts with `192.168...` or `10...`) and run:
```bash
python mobile_sender.py <YOUR_PC_IP_ADDRESS>
```

---

## 🎤 Usage in Apps (Discord/Zoom/OBS)

1.  Open your app's **Voice/Audio Settings**.
2.  Set **Input Device** to: `Wireless_Microphone_Mobile`.
3.  Set **Output Device** to your normal speakers/headphones.

---

## 🔧 Troubleshooting

| Problem | Solution |
| :--- | :--- |
| **I still hear myself on PC speakers** | Make sure the terminal says `[ SUCCESS ] Moved Stream`. If not, open your system **Sound Settings** and manually move the `python` playback stream to `WifiMicSink`. |
| **No audio in Discord** | Check if the `Wireless_Microphone_Mobile` bar is moving in Sound Settings. If yes, the issue is Discord settings. If no, audio isn't reaching the PC. |
| **Audio is lagging** | Ensure both devices are on the same 5GHz Wi-Fi. 2.4GHz can be too slow for real-time audio. |
| **Virtual devices left behind** | If the script crashes, run: `pactl unload-module module-remap-source` and `pactl unload-module module-null-sink`. |

---

## 📂 Project Structure
- `pc_receiver.py`: Main PC script (Logic for Sink/Source/Routing).
- `Termux/mobile_sender.py`: Phone script (Audio capture & UDP transport).
- `README.md`: This guide.
