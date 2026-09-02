# Codebase Walkthrough

This document explains the architecture of the MS Rewards Farmer and the purpose of each file in the `src/` directory.

## Core Files

### `src/main.py` (The Orchestrator)
This is the entry point of the script. It manages the global loop, iterating through all defined profiles. For each profile, it:
1. Triggers an IPv6 rotation via `ipv6_manager`.
2. Initializes the Selenium WebDriver with stealth options.
3. Instantiates `RewardsTaskUtils` to run the web tasks.
4. Calculates point deltas (before vs after).
5. Sends beautifully formatted Telegram summaries via `telegram_notifier`.
6. Enforces randomized jitter delays between profile runs.

### `src/rewards_tasks.py` (The Automation Engine)
Contains the `RewardsTaskUtils` class, which handles the actual DOM interactions. It includes logic for:
- Fetching available points from the Rewards Dashboard.
- Navigating to the Earn page to scrape "Today's points".
- Clicking on Daily Set cards, search tasks, and promotional punch cards.
- Gracefully handling timeouts and skipping broken cards.

### `src/element_selectors.py` (The DOM Map)
A centralized dictionary of CSS and XPath selectors used by `rewards_tasks.py`. Abstracting these away from the logic makes the script much easier to maintain when Microsoft changes their UI (e.g., if a button class name changes, you only update it here).

### `src/constants.py` (Configuration)
Stores global configurations such as:
- The `USER_DATA_DIR` path where Chrome profiles are saved.
- The `PROFILES` array (which accounts to run).
- Default wait times, jitter ranges, and retry limits.

## Infrastructure Files

### `src/setup.py` (Initialization)
A standalone script that you run **once**. It sequentially launches a non-headless Edge browser for each profile defined in `constants.py`, allowing you to manually log into your Microsoft accounts. It caches these sessions in `./data-dir/`.

### `src/stealth.py` (Anti-Detection)
Microsoft employs browser fingerprinting. This module uses Chrome DevTools Protocol (CDP) to inject JavaScript into every page before it loads. It spoofs:
- Hardware Concurrency & Device Memory
- WebGL Vendor (`Apple`) & Renderer strings
- The browser Timezone (`Asia/Kolkata` by default)
The values are deterministically seeded based on the profile name, ensuring that "Profile 1" always looks like the exact same computer, while "Profile 2" looks like a completely different computer.

### `src/ipv6_manager.py` (Network Identity)
To prevent IP bans from multiple accounts operating from the same house, this script cycles the network interface (turning Wi-Fi off and on). Because most modern ISPs use IPv6 SLAAC, reconnecting to the network forces the router to assign a brand new public IPv6 address. It verifies the IP change via an external API before proceeding.

### `src/telegram_notifier.py` (Alerts)
Handles all communication with the Telegram API. It runs a lightweight background daemon thread with a message queue. This ensures that network latency or Telegram API rate limits (`429 Too Many Requests`) never block or slow down the Selenium web scraping process.
