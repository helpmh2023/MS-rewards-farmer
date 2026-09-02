from os.path import abspath

# Dedicated data directory for Selenium — NOT the system Edge profile.
# This lives inside the project root and is fully owned by the script.
# Each subfolder is one profile, created on first run.
USER_DATA_DIR = abspath("./data-dir")

# Profile folder names inside USER_DATA_DIR.
# These are created automatically by Edge on first launch.
PROFILES = [
    "Default",    # Rewards 1
    "Profile 1",  # Rewards 2
    "Profile 2",  # Rewards 3
    "Profile 3",  # Rewards 4
]

# Human-readable display labels (shown in terminal output)
PROFILE_LABELS = {
    "Default":   "Rewards 1",
    "Profile 1": "Rewards 2",
    "Profile 2": "Rewards 3",
    "Profile 3": "Rewards 4",
}

# Gap between consecutive profiles (seconds)
INTER_PROFILE_WAIT   = 10 * 60   # 10 minutes
INTER_PROFILE_JITTER = 30        # ±30 seconds random jitter