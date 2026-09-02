"""One-time setup: sign each profile into rewards.bing.com.

Run this ONCE before using main.py. It opens Edge for each profile
so you can manually sign in. The login cookie is then saved in ./data-dir
and main.py reuses it every time.

Usage (from the project root):
    python src/setup.py

You can also set up just one profile:
    python src/setup.py "Profile 1"
"""

import sys
import time

from selenium import webdriver
from constants import USER_DATA_DIR, PROFILES, PROFILE_LABELS
import stealth


def open_profile_for_setup(profile: str, label: str):
    options = webdriver.EdgeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument(f"--profile-directory={profile}")

    print(f"\n  Opening Edge for: {label} ({profile})")
    print(f"  → Go to:  https://rewards.bing.com/")
    print(f"  → Sign in with this profile's Microsoft account")
    print(f"  → Accept any cookie/consent banners")
    print(f"  → Confirm you can see the Rewards dashboard")
    print(f"  → Come back here and press Enter to close Edge and continue")

    driver = webdriver.Edge(options=options)
    stealth.apply_stealth(driver, profile)
    driver.get("https://rewards.bing.com/")

    input("\n  Press Enter once signed in and dashboard is visible > ")

    driver.quit()
    print(f"  ✅ {label} done.\n")


def main():
    # Allow targeting a single profile from the command line
    target = sys.argv[1] if len(sys.argv) > 1 else None

    to_setup = (
        [(target, PROFILE_LABELS.get(target, target))]
        if target
        else [(p, PROFILE_LABELS.get(p, p)) for p in PROFILES]
    )

    print()
    print("=" * 58)
    print("  MS Rewards Farmer — One-Time Profile Setup")
    print("=" * 58)
    print(f"\n  This will open Edge for {len(to_setup)} profile(s).")
    print("  Sign in to rewards.bing.com in each one.")
    print("  Press Ctrl+C at any time to stop.\n")

    for profile, label in to_setup:
        open_profile_for_setup(profile, label)

    print("=" * 58)
    print("  Setup complete! You can now run:  python src/main.py")
    print("=" * 58)
    print()


if __name__ == "__main__":
    main()
