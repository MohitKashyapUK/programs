# WifiMic: Android to Arch Linux Wireless Microphone (Hotspot Optimized)

Transform your Android phone into a high-quality wireless microphone for your Arch Linux PC. This version is optimized for **Mobile Hotspot** usage, bypassing PC firewall issues and providing zero-configuration setup.

---

## 🚀 How it Works

1.  **Mobile as Server**: The `mobile_sender.py` (running in Termux) starts a TCP server. It captures audio from your phone and waits for the PC to connect.
2.  **PC as Client**: The `pc_receiver.py` automatically detects your phone's IP (via the Default Gateway) and connects to it to "pull" the audio.
3.  **Firewall Friendly**: Since the PC initiates the connection (Outgoing traffic), Arch Linux's firewall usually allows it without any special configuration.
4.  **Virtual Mic**: The audio is routed into a virtual "Null Sink" and remapped to a virtual source, which apps like Discord/Zoom see as a real microphone.

---

## 🛠️ Arch Linux Setup (PC)

### 1. Install Dependencies
```bash
sudo pacman -S python python-pyaudio libpulse
```

### 2. Running the Receiver
Simply connect your PC to your phone's Hotspot (or have them on the same Wi-Fi) and run:
```bash
cd WifiMic
python pc_receiver.py
```
*Note: It will automatically detect your phone's IP. No manual typing required.*

---

## 📱 Termux Setup (Mobile)

### 1. Install Dependencies
Run these commands inside Termux:
```bash
pkg update && pkg upgrade
pkg install python portaudio clang
pip install pyaudio
```

### 2. Permissions
Ensure **Microphone** permission is enabled for Termux in Android Settings.

### 3. Running the Sender
```bash
python mobile_sender.py
```

---

## 🎤 Usage in Apps (Discord/Zoom/OBS)

1.  Start the **Mobile Sender** first, then start the **PC Receiver**.
2.  Open your app's **Voice/Audio Settings**.
3.  Set **Input Device** to: `Wireless_Microphone_Mobile`.
4.  Set **Output Device** to your normal speakers/headphones.

---

## 🔧 Troubleshooting

| Problem | Solution |
| :--- | :--- |
| **I hear myself on PC speakers** | The script tries to auto-route. If it fails, open **Sound Settings** and move the `python` playback stream to `WifiMicSink`. |
| **PC cannot find Mobile IP** | Ensure you are connected to the phone's Hotspot. If using a normal Wi-Fi router, you might need to provide the IP manually: `python pc_receiver.py <MOBILE_IP>`. |
| **Connection Timeout** | Check if Termux is actually running the script and has permissions. |
| **Cleanup** | If virtual devices are left behind after a crash, run: `pactl unload-module module-remap-source` and `pactl unload-module module-null-sink`. |

---

## 📂 Project Structure
- `pc_receiver.py`: PC client with auto-gateway detection and virtual mic setup.
- `Termux/mobile_sender.py`: Mobile TCP server for audio transport.
- `README.md`: This guide.
