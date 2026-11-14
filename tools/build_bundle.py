#!/usr/bin/env python3
"""Encrypt the scorecard's data into one bundle that only signed-in leadership can open.

    site/data/enc/<id>.bin = 12-byte IV || AES-256-GCM( gzip(JSON) )      (same wire format as the portals)
    key  = HMAC-SHA256(secret, "exec:<epoch>")          -> handed out by the Exec Scorecard Login Apps Script
    id   = sha256("exec:<epoch>").hexdigest()[:16]       -> the file name

The JSON holds the config and every CSV the page reads. It uses the real local build (site/config.local.json +
site/data/local/, from tools/build_local.py) when it exists, otherwise the sample. The secret lives in
.exec-secret.json (gitignored, never published).
"""
import base64, gzip, hashlib, hmac, json, os, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sec = json.loads((ROOT / ".exec-secret.json").read_text())
salted = f"exec:{sec['epoch']}"
key = hmac.new(sec["secret"].encode(), salted.encode(), hashlib.sha256).digest()
bid = hashlib.sha256(salted.encode()).hexdigest()[:16]

local = SITE / "config.local.json"
cfg = json.loads((local if local.exists() else SITE / "config.json").read_text())
files = {}
for name, rel in cfg.get("files", {}).items():
    p = SITE / rel
    files[name] = p.read_text() if p.exists() else ""
payload = {"config": cfg, "files": files, "source": "local" if local.exists() else "sample"}

gz = gzip.compress(json.dumps(payload, separators=(",", ":")).encode(), 9)
iv = os.urandom(12)
blob = iv + AESGCM(key).encrypt(iv, gz, None)
out = SITE / "data" / "enc"
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("*.bin"):
    if old.name != f"{bid}.bin":
        try: old.unlink()
        except OSError: pass
(out / f"{bid}.bin").write_bytes(blob)
assert json.loads(gzip.decompress(AESGCM(key).decrypt(blob[:12], blob[12:], None)))["files"].keys() == files.keys()
print(f"bundle {bid}.bin  ({len(blob):,} bytes, {payload['source']} data, {sum(1 for v in files.values() if v)} files)")
