"""IPv6 interface rotation and public IP tracking for macOS.

Dynamically detects the primary active network interface (e.g. en0, en1),
maps it to the corresponding macOS network service (e.g. Ethernet, Wi-Fi),
refreshes the IPv6 temporary SLAAC configuration, waits for router
negotiation settle time (7 seconds), and logs IPv6 address changes.
"""

import json
import re
import subprocess
import time
import urllib.request
import urllib.error

# Settle time (in seconds) after reconnecting/re-enabling IPv6
# to allow SLAAC router advertisements to negotiate new temporary addresses.
SETTLE_TIME_SECONDS = 7


def get_active_interface_and_service() -> tuple[str, str]:
	"""Find default network interface (e.g. 'en0') and service name (e.g. 'Ethernet' or 'Wi-Fi')."""
	dev = "en0"
	try:
		out = subprocess.check_output(["route", "-n", "get", "default"], text=True)
		m = re.search(r"interface:\s*(\w+)", out)
		if m:
			dev = m.group(1)
	except Exception:
		pass

	service = "Ethernet"
	try:
		hw_out = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
		current_port = None
		for line in hw_out.splitlines():
			if line.startswith("Hardware Port:"):
				current_port = line.split(":", 1)[1].strip()
			elif line.startswith("Device:"):
				device_name = line.split(":", 1)[1].strip()
				if device_name == dev and current_port:
					service = current_port
					break
	except Exception:
		pass

	return dev, service


def get_public_ipv6(timeout: int = 5) -> str:
	"""Fetch the current public IPv6 address.

	Uses system `curl -6` first to explicitly force IPv6 socket binding at
	the OS level, falling back to urllib if needed.
	"""
	urls = [
		"https://api64.ipify.org?format=json",
		"https://api6.ipify.org?format=json",
		"https://v6.ident.me",
		"https://ipv6.icanhazip.com",
	]

	# Strategy 1: system curl -6 (forces IPv6 socket on macOS)
	for url in urls:
		try:
			out = subprocess.check_output(
				["curl", "-6", "-s", "-m", str(timeout), url],
				text=True,
				stderr=subprocess.DEVNULL,
			).strip()
			if "json" in url:
				ip = json.loads(out).get("ip", "")
			else:
				ip = out
			if ":" in ip:
				return ip
		except Exception:
			continue

	# Strategy 2: urllib fallback
	for url in urls:
		try:
			req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
			with urllib.request.urlopen(req, timeout=timeout) as resp:
				data = resp.read().decode("utf-8").strip()
				if "json" in url:
					ip = json.loads(data).get("ip", "")
				else:
					ip = data
				if ":" in ip:
					return ip
		except Exception:
			continue

	return "Unavailable"




def rotate_ipv6() -> tuple[str, str, bool]:
	"""Rotate temporary IPv6 address on macOS.

	Returns:
		tuple of (old_ip, new_ip, success_flag)
	"""
	dev, service = get_active_interface_and_service()
	old_ip = get_public_ipv6()

	print(f"[IPv6] Active interface: {dev} ({service})")
	print(f"[IPv6] Pre-rotation IPv6: {old_ip}")
	print(f"[IPv6] Resetting IPv6 interface state on '{service}'...")

	try:
		if service.lower() == "wi-fi":
			try:
				subprocess.run(["networksetup", "-setairportpower", dev, "off"], capture_output=True)
				time.sleep(2)
			finally:
				subprocess.run(["networksetup", "-setairportpower", dev, "on"], capture_output=True)
		else:
			try:
				subprocess.run(["networksetup", "-setv6off", service], capture_output=True)
				time.sleep(2)
			finally:
				subprocess.run(["networksetup", "-setv6automatic", service], capture_output=True)
	except Exception as exc:
		print(f"[IPv6] [WARNING] Error resetting network interface: {exc}")


	print(f"[IPv6] Waiting {SETTLE_TIME_SECONDS}s for SLAAC IPv6 negotiation...")
	time.sleep(SETTLE_TIME_SECONDS)

	new_ip = get_public_ipv6()
	changed = (new_ip != old_ip) and (new_ip != "Unavailable")

	if changed:
		print(f"[IPv6] ✅ IP successfully rotated! New IPv6: {new_ip}")
	else:
		print(f"[IPv6] ℹ️ Current IPv6: {new_ip}")

	return old_ip, new_ip, changed
