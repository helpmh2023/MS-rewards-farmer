# Headless MS Rewards Farmer

A Python-based, fully automated Microsoft Rewards farming script designed to safely run multiple accounts sequentially. It uses Playwright/Selenium (via Edge), dynamic CDP fingerprint spoofing, IPv6 rotation, and Telegram notifications.

## 🌟 Features
* **Multi-Account Orchestration**: Loops through multiple Edge profiles automatically using isolated local data directories.
* **Network Stealth (IPv6 Rotation)**: Toggles the system's Wi-Fi interface between runs to force a new IPv6 address, preventing IP-level clustering bans.
* **Canvas/WebGL Spoofing**: Injects custom JavaScript via CDP to spoof hardware concurrency, device memory, WebGL vendor, and timezone.
* **Telegram Bot Integration**: Real-time push notifications to your phone on script start, IP rotation, per-account progress, and final summary.
* **Headless Background Execution**: Runs silently in the background without stealing mouse/keyboard focus.

---

## 🛠️ First-Time Setup

This script was originally built for **macOS**, but works on Windows/Linux with minor tweaks to the network interface toggling logic.

### 1. Prerequisites
- **Python 3.10+**
- **Poetry** (for dependency management)
- **Microsoft Edge** browser installed.

### 2. Installation
```bash
git clone git@github.com:helpmh2023/MS-rewards-farmer.git
cd MS-rewards-farmer

# Install Python dependencies
poetry install

# If using Playwright (or Selenium requires browser binaries):
poetry run playwright install chromium
```

### 3. Setup Browser Profiles (One-Time Login)
The script uses a localized folder (`./data-dir`) to store your browser cookies and sessions so you don't have to log in every day.
Run the setup script to open standard browser windows. Log into your Microsoft account manually for each profile. Once logged in, close the window, and the script will prompt you for the next one.
```bash
poetry run python src/setup.py
```

### 4. Setup Telegram Notifications (Optional but recommended)
To get updates on your phone:
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the steps to get an HTTP API Token.
3. In the project folder, create a file named `telegram_config.json`:
   ```json
   {
     "bot_token": "YOUR_TOKEN_HERE",
     "chat_id": null
   }
   ```
4. Run the setup script to link your chat:
   ```bash
   poetry run python src/telegram_notifier.py setup
   ```
   *Send `/start` to your new bot in Telegram when prompted!*

---

## 🚀 Running the Farmer
Once logged in and configured, simply run:
```bash
poetry run python src/main.py
```

## 🐧 Notes for Windows / Linux Users
By default, `src/ipv6_manager.py` uses macOS `networksetup` commands to toggle `en0` (Wi-Fi) off and on to rotate IP addresses.
* **Windows**: You will need to modify `ipv6_manager.py` to use `netsh interface set interface "Wi-Fi" disable / enable` or `ipconfig /release6 && ipconfig /renew6`.
* **Linux**: Modify `ipv6_manager.py` to use `nmcli radio wifi off && nmcli radio wifi on` or `ip link set wlan0 down && ip link set wlan0 up`.

## ⚠️ Disclaimer
Automated farming violates Microsoft's Terms of Service. This code is provided for educational purposes only. The authors are not responsible for banned accounts or lost points. Use at your own risk.
