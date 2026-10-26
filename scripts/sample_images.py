"""Resolve album art and artist photos for the sample listeners, once.

Writes backend/sample_images.json so demo rooms show the same artwork as
real ones without a Spotify call at runtime.
"""
import base64, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.samples import SAMPLES  # noqa: E402

for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

basic = base64.b64encode(f"{os.environ['SPOTIFY_CLIENT_ID']}:{os.environ['SPOTIFY_CLIENT_SECRET']}".encode()).decode()
req = urllib.request.Request("https://accounts.spotify.com/api/token", data=b"grant_type=client_credentials", headers={"Authorization": f"Basic {basic}"})
token = json.load(urllib.request.urlopen(req))["access_token"]


def search(q, kind):
    url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode({"q": q, "type": kind, "limit": 1})
    r = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    items = json.load(urllib.request.urlopen(r))[kind + "s"]["items"]
    return items[0] if items else None


out = {"tracks": {}, "artists": {}, "years": {}}
for s in SAMPLES:
    for key in ("top_tracks_short", "top_tracks_long", "recent"):
        for t in s[key]:
            k = f"{t['name']}|{t['artist']}"
            if k in out["tracks"]:
                continue
            hit = search(f"track:{t['name']} artist:{t['artist']}", "track")
            imgs = (hit or {}).get("album", {}).get("images") or []
            out["tracks"][k] = imgs[1]["url"] if len(imgs) > 1 else (imgs[0]["url"] if imgs else None)
            date = (hit or {}).get("album", {}).get("release_date") or ""
            out["years"][k] = int(date[:4]) if date[:4].isdigit() else None
            time.sleep(0.15)
    for key in ("top_artists_short", "top_artists_long"):
        for a in s[key]:
            if a["name"] in out["artists"]:
                continue
            hit = search(a["name"], "artist")
            imgs = (hit or {}).get("images") or []
            out["artists"][a["name"]] = imgs[1]["url"] if len(imgs) > 1 else (imgs[0]["url"] if imgs else None)
            time.sleep(0.15)

(ROOT / "backend" / "sample_images.json").write_text(json.dumps(out, indent=1, sort_keys=True))
missing = [k for d in (out["tracks"], out["artists"]) for k, v in d.items() if not v]
print(len(out["tracks"]), "tracks", len(out["artists"]), "artists", "missing:", missing)
