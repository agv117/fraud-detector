#!/usr/bin/env python3
"""Deploy the Ledger Autopsy to anandvaghasia.com/fraud-detector/ via FTP_TLS.

Reads ANANDVAGHASIA_FTP_* from ~/.claude/secrets.env. Uploads ONLY into the
fraud-detector/ subdir. Asserts the cwd is that slug before any STOR, never
deletes anything, and NEVER touches /certs.
"""
import os
from ftplib import FTP_TLS, FTP
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRETS = Path.home() / ".claude" / "secrets.env"
REMOTE_ROOT = "fraud-detector"  # relative to the FTP homedir (public_html)

FILES = ["index.html", "styles.css", "app.js"]
DATA = ["data/cases.json"]


def load_env(path):
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def connect(host, user, pw):
    for klass in (FTP_TLS, FTP):
        try:
            ftp = klass()
            ftp.connect(host, 21, timeout=30)
            ftp.login(user, pw)
            if isinstance(ftp, FTP_TLS):
                ftp.prot_p()
            print(f"Connected via {klass.__name__} as {user}")
            return ftp
        except Exception as e:
            print(f"{klass.__name__} failed: {e}")
    raise SystemExit("Could not connect")


def ensure_cwd(ftp, path):
    for part in [p for p in path.split("/") if p]:
        try:
            ftp.cwd(part)
        except Exception:
            ftp.mkd(part)
            ftp.cwd(part)


def main():
    env = load_env(SECRETS)
    host, user, pw = (env.get("ANANDVAGHASIA_FTP_HOST"),
                      env.get("ANANDVAGHASIA_FTP_USER"),
                      env.get("ANANDVAGHASIA_FTP_PASS"))
    if not (host and user and pw):
        raise SystemExit("Missing ANANDVAGHASIA_FTP_* in secrets.env")

    ftp = connect(host, user, pw)
    ensure_cwd(ftp, REMOTE_ROOT)
    here = ftp.pwd()
    # hard guard: refuse to write anywhere that is not the slug dir
    assert here.rstrip("/").endswith(REMOTE_ROOT), f"refuse: cwd is {here}, not the fraud-detector dir"
    print(f"Uploading into {here}")

    total = 0
    for f in FILES:
        src = HERE / f
        with open(src, "rb") as fh:
            ftp.storbinary(f"STOR {f}", fh)
        total += src.stat().st_size
        print(f"  {f} ({src.stat().st_size:,} b)")

    try:
        ftp.cwd("data")
    except Exception:
        ftp.mkd("data")
        ftp.cwd("data")
    for f in DATA:
        src = HERE / f
        name = os.path.basename(f)
        with open(src, "rb") as fh:
            ftp.storbinary(f"STOR {name}", fh)
        total += src.stat().st_size
        print(f"  {f} ({src.stat().st_size:,} b)")

    ftp.quit()
    print(f"\nDone. {total:,} bytes. Live: https://anandvaghasia.com/fraud-detector/")


if __name__ == "__main__":
    main()
