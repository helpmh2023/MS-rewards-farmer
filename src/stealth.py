"""Browser fingerprint anti-detection for MS Rewards farmer.

Injects comprehensive JavaScript overrides via CDP on every new page.
Each profile gets unique but stable fake hardware/fingerprint values
derived deterministically from the profile name, so the same profile
always looks like the same device across daily runs.

All profiles use IST (Asia/Kolkata) as their timezone.

Vectors covered:
    - navigator.webdriver       (Selenium detection flag)
    - Canvas 2D noise           (unique ±1 pixel noise per profile)
    - WebGL vendor/renderer     (fake GPU string per profile)
    - WebGL readPixels noise    (1-byte noise on pixel reads)
    - AudioContext noise        (seeded offset on buffer data)
    - navigator.hardwareConcurrency  (fake CPU core count)
    - navigator.deviceMemory         (fake RAM amount)
    - navigator.platform             (Win32 / MacIntel)
    - navigator.languages / language (en-IN biased)
    - navigator.plugins              (minimal realistic set)
    - screen dimensions              (unique realistic resolution)
    - window.devicePixelRatio
    - window.chrome                  (minimal chrome object)
    - Battery API                    (fake charging level)
    - Network info API               (fake downlink / effectiveType)
    - Timezone                       (Asia/Kolkata via CDP)
    - Locale                         (en-IN via CDP)
"""

import hashlib
import random
from typing import Any

from selenium import webdriver


# ---------------------------------------------------------------------------
# Realistic value pools
# ---------------------------------------------------------------------------

_CPU_CORES = [4, 6, 8, 8, 12]

_RAM_GB = [4, 8, 8, 16]

_SCREENS = [
	# (width, height, availWidth, availHeight)
	(1920, 1080, 1920, 1040),
	(2560, 1440, 2560, 1400),
	(1366, 768,  1366, 728),
	(1440, 900,  1440, 860),
	(1280, 800,  1280, 760),
	(1600, 900,  1600, 860),
]

_PLATFORMS = ["Win32", "Win32", "Win32", "MacIntel"]  # bias toward Windows

_WEBGL_GPUS = [
	("Intel Inc.", "Intel Iris OpenGL Engine"),
	("NVIDIA Corporation", "NVIDIA GeForce GTX 1060/PCIe/SSE2"),
	("AMD", "AMD Radeon RX 570 Series"),
	("Intel Inc.", "Intel UHD Graphics 630"),
	("NVIDIA Corporation", "NVIDIA GeForce GTX 960M/PCIe/SSE2"),
	("Intel Inc.", "Intel HD Graphics 520"),
]

_LANGUAGES = [
	["en-IN", "en-US", "en"],
	["en-IN", "en", "hi"],
	["en-US", "en-IN", "en"],
	["en-IN", "en-GB", "en"],
]

# All profiles report India Standard Time
_TIMEZONE = "Asia/Kolkata"
_LOCALE   = "en-IN"


# ---------------------------------------------------------------------------
# Fingerprint generation
# ---------------------------------------------------------------------------

def _seed(profile: str) -> random.Random:
	"""Return a deterministic RNG seeded by the profile name."""
	h = int(hashlib.sha256(profile.encode()).hexdigest(), 16)
	return random.Random(h)


def _generate_fingerprint(profile: str) -> dict[str, Any]:
	"""Return a stable, unique-per-profile set of fake hardware values."""
	rng    = _seed(profile)
	screen = rng.choice(_SCREENS)
	gpu    = rng.choice(_WEBGL_GPUS)

	return {
		"cpu_cores":        rng.choice(_CPU_CORES),
		"ram_gb":           rng.choice(_RAM_GB),
		"platform":         rng.choice(_PLATFORMS),
		"languages":        rng.choice(_LANGUAGES),
		"screen_w":         screen[0],
		"screen_h":         screen[1],
		"avail_w":          screen[2],
		"avail_h":          screen[3],
		"color_depth":      24,
		"pixel_ratio":      rng.choice([1, 1, 1, 2]),
		"webgl_vendor":     gpu[0],
		"webgl_renderer":   gpu[1],
		"canvas_seed":      rng.randint(1, 1_000_000),
		"audio_noise":      rng.uniform(0.00001, 0.0001),
		"battery_level":    round(rng.uniform(0.60, 0.99), 2),
		"battery_charging": rng.choice([True, False]),
		"downlink":         rng.choice([10, 50, 100]),
		"timezone":         _TIMEZONE,
		"locale":           _LOCALE,
	}


# ---------------------------------------------------------------------------
# JS patch builder
# ---------------------------------------------------------------------------

def _build_js_patch(fp: dict[str, Any]) -> str:
	"""Build the comprehensive JS override block to inject on every page."""

	langs_js       = str(fp["languages"])
	battery_charge = "true" if fp["battery_charging"] else "false"
	discharge_time = "Infinity" if fp["battery_charging"] else "3600"

	return f"""
(function() {{

// ── navigator.webdriver ────────────────────────────────────────────────────
Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

// ── Hardware ───────────────────────────────────────────────────────────────
Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp["cpu_cores"]} }});
Object.defineProperty(navigator, 'deviceMemory',        {{ get: () => {fp["ram_gb"]} }});
Object.defineProperty(navigator, 'platform',            {{ get: () => '{fp["platform"]}' }});
Object.defineProperty(navigator, 'languages',           {{ get: () => {langs_js} }});
Object.defineProperty(navigator, 'language',            {{ get: () => '{fp["languages"][0]}' }});

// ── Plugins (realistic minimal set) ───────────────────────────────────────
(function() {{
    const _p = [
        {{ name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer',           description: 'Portable Document Format' }},
        {{ name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
        {{ name: 'Native Client',      filename: 'internal-nacl-plugin',          description: '' }},
    ];
    try {{
        Object.defineProperty(navigator, 'plugins', {{
            get: () => Object.assign(Object.create(PluginArray.prototype), _p)
        }});
    }} catch(e) {{}}
}})();

// ── Screen ─────────────────────────────────────────────────────────────────
Object.defineProperty(screen, 'width',       {{ get: () => {fp["screen_w"]} }});
Object.defineProperty(screen, 'height',      {{ get: () => {fp["screen_h"]} }});
Object.defineProperty(screen, 'availWidth',  {{ get: () => {fp["avail_w"]} }});
Object.defineProperty(screen, 'availHeight', {{ get: () => {fp["avail_h"]} }});
Object.defineProperty(screen, 'colorDepth',  {{ get: () => {fp["color_depth"]} }});
Object.defineProperty(screen, 'pixelDepth',  {{ get: () => {fp["color_depth"]} }});
Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {fp["pixel_ratio"]} }});

// ── window.chrome ──────────────────────────────────────────────────────────
window.chrome = {{
    runtime: {{}},
    loadTimes: function() {{ return {{}}; }},
    csi:        function() {{ return {{}}; }},
    app:        {{ isInstalled: false }}
}};

// ── Canvas 2D — ±1 noise per pixel, seeded per profile ────────────────────
(function() {{
    const SEED = {fp["canvas_seed"]};
    const _origGetCtx = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {{
        const ctx = _origGetCtx.call(this, type, ...args);
        if (type === '2d' && ctx && !ctx.__noised) {{
            ctx.__noised = true;
            const _origGID = ctx.getImageData.bind(ctx);
            ctx.getImageData = function(x, y, w, h) {{
                const img = _origGID(x, y, w, h);
                let s = SEED;
                for (let i = 0; i < img.data.length; i += 4) {{
                    s = (Math.imul(s, 1664525) + 1013904223) | 0;
                    const n = (s >>> 31) ? 1 : -1;
                    img.data[i]     = Math.max(0, Math.min(255, img.data[i]     + n));
                    img.data[i + 1] = Math.max(0, Math.min(255, img.data[i + 1] + n));
                    img.data[i + 2] = Math.max(0, Math.min(255, img.data[i + 2] + n));
                }}
                return img;
            }};
        }}
        return ctx;
    }};
}})();

// ── WebGL — fake GPU vendor/renderer + readPixels noise ───────────────────
(function() {{
    const VENDOR   = '{fp["webgl_vendor"]}';
    const RENDERER = '{fp["webgl_renderer"]}';
    const UNMASKED_VENDOR   = 0x9245;
    const UNMASKED_RENDERER = 0x9246;

    function patchWebGL(ctx) {{
        if (!ctx || ctx.__patched) return ctx;
        ctx.__patched = true;

        const _origGetParam = ctx.getParameter.bind(ctx);
        ctx.getParameter = function(p) {{
            if (p === UNMASKED_VENDOR)   return VENDOR;
            if (p === UNMASKED_RENDERER) return RENDERER;
            return _origGetParam(p);
        }};

        const _origReadPixels = ctx.readPixels.bind(ctx);
        ctx.readPixels = function(x, y, w, h, fmt, type, buf) {{
            _origReadPixels(x, y, w, h, fmt, type, buf);
            if (buf && buf.length > 0) buf[0] = (buf[0] + 1) & 0xff;
        }};
        return ctx;
    }}

    const _origGetCtx = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = (function(orig) {{
        return function(type, ...args) {{
            const ctx = orig.call(this, type, ...args);
            if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') {{
                return patchWebGL(ctx);
            }}
            return ctx;
        }};
    }})(_origGetCtx);
}})();

// ── AudioContext — seeded buffer noise ────────────────────────────────────
(function() {{
    const NOISE = {fp["audio_noise"]};
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;

    const _origAnalyser = AC.prototype.createAnalyser;
    AC.prototype.createAnalyser = function() {{
        const node = _origAnalyser.call(this);
        const _origFloat = node.getFloatFrequencyData.bind(node);
        node.getFloatFrequencyData = function(arr) {{
            _origFloat(arr);
            for (let i = 0; i < arr.length; i++) arr[i] += NOISE;
        }};
        return node;
    }};

    const _origOSN = AC.prototype.createOscillator;
    if (_origOSN) {{
        AC.prototype.createOscillator = function() {{
            const osc = _origOSN.call(this);
            const _origConn = osc.connect.bind(osc);
            osc.connect = function(dest, ...args) {{
                return _origConn(dest, ...args);
            }};
            return osc;
        }};
    }}
}})();

// ── Battery API ───────────────────────────────────────────────────────────
if (navigator.getBattery) {{
    navigator.getBattery = () => Promise.resolve({{
        charging:        {battery_charge},
        chargingTime:    Infinity,
        dischargingTime: {discharge_time},
        level:           {fp["battery_level"]},
        addEventListener:    function() {{}},
        removeEventListener: function() {{}}
    }});
}}

// ── Network info ──────────────────────────────────────────────────────────
try {{
    if (navigator.connection) {{
        const _conn = {{
            effectiveType: '4g',
            downlink:      {fp["downlink"]},
            rtt:           50,
            saveData:      false,
            addEventListener:    function() {{}},
            removeEventListener: function() {{}}
        }};
        Object.defineProperty(navigator, 'connection', {{ get: () => _conn }});
    }}
}} catch(e) {{}}

}})();
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_stealth(driver: webdriver.Edge, profile: str) -> None:
	"""Inject all fingerprint spoofing into an already-created driver.

	Call this immediately after `webdriver.Edge(options=options)` and
	before navigating to any page.

	Args:
		driver:  The newly created Edge WebDriver instance.
		profile: Profile folder name (e.g. "Default", "Profile 1").
		         Used as a deterministic seed for all fake values.
	"""
	fp = _generate_fingerprint(profile)

	# JS block — injected into every document the driver opens
	driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
		"source": _build_js_patch(fp)
	})

	# Timezone — Asia/Kolkata for all profiles
	try:
		driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {
			"timezoneId": fp["timezone"]
		})
	except Exception:
		pass  # non-fatal

	# Locale
	try:
		driver.execute_cdp_cmd("Emulation.setLocaleOverride", {
			"locale": fp["locale"]
		})
	except Exception:
		pass  # non-fatal

	print(
		f"[STEALTH] {profile}: "
		f"{fp['cpu_cores']} cores | "
		f"{fp['ram_gb']} GB RAM | "
		f"{fp['screen_w']}x{fp['screen_h']} | "
		f"{fp['platform']} | "
		f"GPU: {fp['webgl_renderer'].split('/')[0]} | "
		f"TZ: {fp['timezone']}"
	)
