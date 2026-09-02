import json
import os
import queue
import sys
import threading
import time
import urllib.request
import urllib.error
import urllib.parse

CONFIG_FILE = "telegram_config.json"
_msg_queue = queue.Queue()
_worker_thread = None
_config = {}

def load_config():
    global _config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                _config = json.load(f)
        except Exception as e:
            print(f"[Telegram] Error loading config: {e}")
    return _config

def save_config(config_dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_dict, f, indent=2)

def _api_call(method: str, data: dict = None) -> dict:
    if "bot_token" not in _config or not _config["bot_token"]:
        return {}
    
    url = f"https://api.telegram.org/bot{_config['bot_token']}/{method}"
    
    try:
        if data:
            req_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=req_data)
        else:
            req = urllib.request.Request(url)
            
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            return res
    except Exception as e:
        print(f"[Telegram Error] API call to {method} failed: {e}")
        return {}

def _worker():
    while True:
        msg = _msg_queue.get()
        if msg is None:  # Sentinel to exit
            _msg_queue.task_done()
            break
            
        if _config.get("chat_id"):
            _api_call("sendMessage", {
                "chat_id": _config["chat_id"],
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            })
            time.sleep(1.2)  # Respect Telegram's ~1 msg/sec rate limit
            
        _msg_queue.task_done()

def init():
    """Initialize the background worker thread."""
    global _worker_thread
    load_config()
    
    if not _config.get("bot_token") or not _config.get("chat_id"):
        return False
        
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()
    return True

def send_message(text: str):
    """Enqueue a message to be sent to Telegram."""
    if not _config.get("chat_id"):
        return
    _msg_queue.put(text)

def wait_and_close():
    """Wait for all pending messages to be sent, then close the thread."""
    if _worker_thread and _worker_thread.is_alive():
        _msg_queue.join()
        _msg_queue.put(None)
        _worker_thread.join(timeout=5)

def setup():
    """Interactive CLI to get the user's chat ID."""
    print("=== Telegram Bot Setup ===")
    load_config()
    
    if not _config.get("bot_token"):
        print("Error: bot_token not found in telegram_config.json")
        return
        
    print("1. Open Telegram and search for your bot.")
    print("2. Send the message '/start' or 'ping' to the bot.")
    print("3. Waiting for your message... (Polling for 60 seconds)")
    
    start_time = time.time()
    offset = 0
    
    while time.time() - start_time < 60:
        res = _api_call("getUpdates", {"offset": offset, "timeout": 5})
        if res and res.get("ok"):
            for update in res.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    username = update["message"]["from"].get("username", "Unknown")
                    
                    print(f"\nReceived message from @{username} (chat_id: {chat_id})")
                    print("Saving chat_id to config...")
                    
                    _config["chat_id"] = chat_id
                    save_config(_config)
                    
                    # Send a confirmation message
                    init()
                    send_message("✅ *MS Rewards Farmer*\nSuccessfully paired with this chat! You will now receive terminal updates here.")
                    wait_and_close()
                    
                    print("Setup complete! You can now run the farmer.")
                    return
        time.sleep(1)
        
    print("\nTimeout. No messages received. Try again.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        print("Run 'python src/telegram_notifier.py setup' to configure the bot.")
