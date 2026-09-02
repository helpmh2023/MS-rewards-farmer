"""Multi-profile Microsoft Rewards farmer.

Cycles through pre-configured Edge profiles (each already signed into a
different Microsoft Rewards account) and completes all reward tasks. Tracks
total points earned per profile and prints formatted summaries.

Usage (from the project root):
    python src/main.py

Prerequisites:
    - Each profile in PROFILES must already be signed into rewards.bing.com
    - Edge must be fully closed before running
    - Ollama must be running (ollama serve, or the macOS app)
"""

import random
import subprocess
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from constants import (
	USER_DATA_DIR,
	PROFILES,
	PROFILE_LABELS,
	INTER_PROFILE_WAIT,
	INTER_PROFILE_JITTER,
)
import rewards_tasks
import stealth
import ipv6_manager
import telegram_notifier



# --------------------------------------------------------------------------
# Driver factory
# --------------------------------------------------------------------------

def create_driver(profile: str) -> webdriver.Edge:
	"""Launch Edge with the given profile inside the local data-dir.

	Uses a dedicated ./data-dir folder that the script owns exclusively,
	so there is no conflict with the system Edge installation.
	"""
	options = webdriver.EdgeOptions()
	options.add_experimental_option("excludeSwitches", ["enable-automation"])
	options.add_experimental_option("useAutomationExtension", False)
	options.add_argument("--disable-blink-features=AutomationControlled")
	options.add_argument("--disable-infobars")
	options.add_argument("--no-first-run")
	options.add_argument("--no-default-browser-check")
	options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
	options.add_argument(f"--profile-directory={profile}")

	driver = webdriver.Edge(options=options)

	# Apply full fingerprint spoofing — canvas, WebGL, audio, hardware,
	# screen, timezone (Asia/Kolkata), locale, navigator overrides.
	stealth.apply_stealth(driver, profile)

	return driver




# --------------------------------------------------------------------------
# Display helpers
# --------------------------------------------------------------------------

TASK_ICON = {"OK": "✅", "SKIP": "⏭ ", "FAIL": "❌"}

def _task_icon(status: str) -> str:
	for key, icon in TASK_ICON.items():
		if status.startswith(key):
			return icon
	return "  "

def _short_status(status: str) -> str:
	return status.split("(")[0].strip() if "(" in status else status


def print_profile_summary(
	index: int,
	total: int,
	label: str,
	profile: str,
	task_results: dict[str, str],
	avail_before: int,
	avail_after: int,
	todays_pts: int,
	session_earned: int | str,
	duration_secs: float,
	ipv6_addr: str = "Unknown",
):
	"""Print the per-profile summary banner."""
	completed_at = datetime.now().strftime("%H:%M:%S")
	mins  = int(duration_secs) // 60
	secs  = int(duration_secs) % 60

	title = f"  Profile {index}/{total}: {label} ({profile})  "
	width = max(len(title) + 2, 58)

	print()
	print(f"╔{'═' * width}╗")
	print(f"║{title.center(width)}║")
	print(f"╠{'═' * width}╣")

	for name, status in task_results.items():
		icon  = _task_icon(status)
		short = _short_status(status)
		line  = f"  {name:<26} →  {icon} {short}"
		print(f"║{line.ljust(width)}║")

	print(f"╠{'═' * width}╣")

	ip_line = f"  IPv6 Address        : {ipv6_addr}"
	print(f"║{ip_line.ljust(width)}║")

	pts_start_line = f"  Available pts (start): {avail_before:,}" if avail_before else "  Available pts (start): ?"
	print(f"║{pts_start_line.ljust(width)}║")

	todays_line = f"  Today's points total: {todays_pts:,}" if todays_pts else "  Today's points total: ?"
	print(f"║{todays_line.ljust(width)}║")

	earned_str = f"+{session_earned}" if isinstance(session_earned, int) else "unknown"
	pts_earned_line = f"  Points this session : {earned_str}"
	print(f"║{pts_earned_line.ljust(width)}║")

	total_line = f"  Total balance now   : {avail_after:,}" if avail_after else "  Total balance now   : ?"
	print(f"║{total_line.ljust(width)}║")

	print(f"╚{'═' * width}╝")
	print(f"  Completed at {completed_at} | Duration: {mins}m {secs:02d}s")
	print()
	
	# Send Telegram Notification
	tg_msg = (
		f"✅ *Profile {index}/{total}: {label}*\n"
		f"⏱ *Duration:* {mins}m {secs:02d}s\n\n"
		f"🌐 *IPv6:* `{ipv6_addr}`\n"
	)
	
	for name, status in task_results.items():
		icon = _task_icon(status)
		short = _short_status(status)
		tg_msg += f"• {name}: {icon} {short}\n"
		
	tg_msg += (
		f"\n💰 *Session Earned:* {earned_str}\n"
		f"📈 *Today's Total:* {todays_pts:,}\n"
		f"🏦 *Total Balance:* {avail_after:,}"
	)
	telegram_notifier.send_message(tg_msg)


def print_final_summary(all_results: list[dict], total_duration: float):
	"""Print the grand summary across all profiles."""
	total_mins = int(total_duration) // 60
	total_secs = int(total_duration) % 60

	grand_earned = sum(
		r["session_earned"] for r in all_results if isinstance(r.get("session_earned"), int)
	)

	width = 68
	print()
	print(f"{'═' * width}")
	print(f"  {'FINAL SUMMARY':^{width - 2}}")
	print(f"{'═' * width}")

	for r in all_results:
		label    = r["label"]
		profile  = r["profile"]
		earned   = r.get("session_earned", "?")
		todays   = r.get("todays_pts", 0)
		balance  = r.get("avail_after", 0)
		ipv6     = r.get("ipv6", "Unknown")
		d_mins   = int(r["duration"]) // 60
		d_secs   = int(r["duration"]) % 60
		ok_n     = sum(1 for v in r["task_results"].values() if v == "OK")
		total_t  = len(r["task_results"])

		earned_str = f"+{earned:,}" if isinstance(earned, int) else "+?"
		after_str  = f"{balance:,}" if balance else "?"
		todays_str = f"{todays:,}" if todays else "?"

		print(
			f"  {label} ({profile})"
			f"\n    IPv6: {ipv6}"
			f"\n    Tasks: {ok_n}/{total_t} OK"
			f"  │  Earned session: {earned_str}"
			f"  │  Today's total: {todays_str}"
			f"  │  Balance: {after_str}"
			f"  │  Time: {d_mins}m {d_secs:02d}s"
		)

	print(f"\n  {'─' * (width - 2)}")
	print(f"  Total points earned today  :  +{grand_earned:,}")
	print(f"  Total runtime              :  {total_mins}m {total_secs:02d}s")
	print(f"{'═' * width}")
	print()
	
	tg_msg = (
		f"🏁 *FARMING COMPLETE*\n"
		f"⏱ *Total Runtime:* {total_mins}m {total_secs:02d}s\n"
		f"🎉 *Total Points Earned Today:* +{grand_earned:,}\n\n"
	)
	for r in all_results:
		lbl = r["label"]
		prof = r["profile"]
		earned = r.get("session_earned", "?")
		bal = r.get("avail_after", 0)
		earned_s = f"+{earned:,}" if isinstance(earned, int) else "+?"
		bal_s = f"{bal:,}" if bal else "?"
		tg_msg += f"• *{lbl}*: {earned_s} (Bal: {bal_s})\n"
		
	telegram_notifier.send_message(tg_msg)
	telegram_notifier.wait_and_close()




# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
	telegram_notifier.init()
	
	print()
	print("=" * 58)
	print(f"  MS Rewards Farmer  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
	print(f"  Profiles to run: {len(PROFILES)}")
	print("=" * 58)
	print()
	
	telegram_notifier.send_message(f"🚀 *MS Rewards Farmer Started*\nProfiles to run: {len(PROFILES)}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
	
	print("  ⚠️  Make sure Edge is fully closed before continuing.")
	print("  Press Enter when ready, or Ctrl+C to abort.")
	input("  > ")
	print()

	all_results: list[dict] = []
	run_start = time.monotonic()

	for index, profile in enumerate(PROFILES):
		label = PROFILE_LABELS.get(profile, profile)

		print(f"{'─' * 58}")
		print(f"  Profile {index + 1}/{len(PROFILES)}: {label} ({profile})")
		print(f"{'─' * 58}")
		telegram_notifier.send_message(f"▶️ *Starting Profile {index + 1}/{len(PROFILES)}:* {label}")

		profile_start = time.monotonic()

		# --- Rotate IPv6 Temporary Address before starting profile ---
		old_ip, active_ipv6, rotated = ipv6_manager.rotate_ipv6()

		driver = None

		try:
			driver = create_driver(profile)
		except WebDriverException as exc:
			print(f"[FAIL] Could not launch Edge with profile '{profile}': {exc}")
			all_results.append({
				"label": label,
				"profile": profile,
				"task_results": {"Launch": f"FAIL ({type(exc).__name__})"},
				"avail_before": 0,
				"avail_after": 0,
				"todays_pts": 0,
				"session_earned": "?",
				"duration": time.monotonic() - profile_start,
				"ipv6": active_ipv6,
			})
			continue

		try:
			farm = rewards_tasks.RewardsTaskUtils(driver)

			# --- Snapshot points BEFORE tasks ---
			print("[INFO] Reading points (before tasks)...")
			avail_before = farm.get_available_points()
			todays_before = farm.get_todays_points()
			print(f"[INFO] Available points (start): {avail_before:,}")
			print(f"[INFO] Today's points (start):    {todays_before:,}")

			# --- Run all 6 reward tasks ---
			task_results = farm.complete_all_tasks()

			# --- Snapshot points AFTER tasks ---
			print("[INFO] Reading points (after tasks)...")
			avail_after = farm.get_available_points()
			todays_after = farm.get_todays_points()
			print(f"[INFO] Available points (now):   {avail_after:,}")
			print(f"[INFO] Today's points (total):  {todays_after:,}")

			if todays_after >= todays_before and (todays_after > 0 or todays_before > 0):
				session_earned = todays_after - todays_before
			elif avail_after >= avail_before:
				session_earned = avail_after - avail_before
			else:
				session_earned = "?"

		except Exception as exc:
			print(f"[FAIL] Unexpected error during profile '{profile}': {exc}")
			task_results   = {"Run": f"FAIL ({type(exc).__name__})"}
			avail_before   = 0
			avail_after    = 0
			todays_after   = 0
			session_earned = "?"
		finally:
			try:
				driver.quit()
			except Exception:
				pass

		profile_duration = time.monotonic() - profile_start

		print_profile_summary(
			index + 1, len(PROFILES),
			label, profile,
			task_results,
			avail_before, avail_after,
			todays_after, session_earned,
			profile_duration,
			ipv6_addr=active_ipv6,
		)

		all_results.append({
			"label": label,
			"profile": profile,
			"task_results": task_results,
			"avail_before": avail_before,
			"avail_after": avail_after,
			"todays_pts": todays_after,
			"session_earned": session_earned,
			"duration": profile_duration,
			"ipv6": active_ipv6,
		})

		# --- Wait between profiles ---
		if index < len(PROFILES) - 1:
			jitter    = random.randint(-INTER_PROFILE_JITTER, INTER_PROFILE_JITTER)
			wait_secs = INTER_PROFILE_WAIT + jitter
			wait_mins = wait_secs // 60
			wait_s    = wait_secs % 60
			
			msg = f"⏳ Waiting {wait_mins}m {wait_s}s before next profile..."
			print(f"{msg}\n")
			telegram_notifier.send_message(f"_{msg}_")
			time.sleep(wait_secs)

	# --- Grand total ---
	print_final_summary(all_results, time.monotonic() - run_start)


if __name__ == "__main__":
	main()