#!/usr/bin/env python3
"""Fetch the Store Director Portal's nightly Executive Scorecard feed and unlock it.

The StorePortal nightly build (sdp/build_site.py) publishes data/<id>.bin, locked with the scorecard's own secret:
    key = HMAC-SHA256(secret, "exec-sdp:<epoch>")      id = sha256("exec-sdp:<epoch>").hexdigest()[:16]
(same wire format as every Big Grove bundle: 12-byte IV || AES-256-GCM(gzip JSON)). This writes the unlocked
payload to inputs/private/sdp_payload.json (gitignored), which tools/build_local.py picks up on its own.

    python3 tools/fetch_sdp.py                 # from https://bgtroy2026.github.io/StorePortal/
    python3 tools/fetch_sdp.py --file X.bin    # a bundle already on disk (testing)
"""
import argparse, gzip, hashlib, hmac, json, sys, urllib.request
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://bgtroy2026.github.io/StorePortal/data/"
OUT = ROOT / "inputs" / "private" / "sdp_payload.json"

ap = argparse.ArgumentParser()
ap.add_argument("--file")
ap.add_argument("--secret", help="override .exec-secret.json (testing)")
a = ap.parse_args()
sec = json.loads((ROOT / ".exec-secret.json").read_text())
secret, epoch = a.secret or sec["secret"], str(sec.get("epoch", "1"))
salted = f"exec-sdp:{epoch}"
key = hmac.new(secret.encode(), salted.encode(), hashlib.sha256).digest()
bid = hashlib.sha256(salted.encode()).hexdigest()[:16]

if a.file:
    blob = Path(a.file).read_bytes()
else:
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}{bid}.bin", headers={"Cache-Control": "no-cache"}), timeout=60) as r:
            blob = r.read()
    except Exception as e:
        sys.exit(f"  ! Store Director feed not reachable ({e}). Is EXEC_SECRET set on the StorePortal repo, and has the nightly run since?")
try:
    payload = json.loads(gzip.decompress(AESGCM(key).decrypt(blob[:12], blob[12:], None)))
except Exception:
    sys.exit("  ! Store Director feed would not unlock — EXEC_SECRET on the StorePortal repo must match .exec-secret.json.")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, separators=(",", ":")))
m = payload.get("meta", {})
print(f"  Store Director feed: {len(payload.get('locations', []))} taprooms, through {m.get('through')} (built {m.get('built_at')})")
