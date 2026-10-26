"""Sample listeners for demo mode.

Spotify apps in Development Mode only let allowlisted accounts sign in, so a
room needs a way to play without five people on the allowlist. These profiles
use real songs and artists so the questions read the same as live ones.
"""


def _tracks(rows: list[tuple[str, str]]) -> list[dict]:
    return [{"name": name, "artist": artist} for name, artist in rows]


def _artists(rows: list[tuple[str, list[str]]]) -> list[dict]:
    return [{"name": name, "genres": genres} for name, genres in rows]


SAMPLES: list[dict] = [
    {
        "name": "Sam",
        "top_tracks_short": _tracks([
            ("Pink + White", "Frank Ocean"), ("Nights", "Frank Ocean"),
            ("Ivy", "Frank Ocean"), ("Redbone", "Childish Gambino"),
            ("Self Control", "Frank Ocean"), ("Get You", "Daniel Caesar"),
            ("Best Part", "Daniel Caesar"), ("Snooze", "SZA"),
        ]),
        "top_tracks_long": _tracks([
            ("Nights", "Frank Ocean"), ("Snooze", "SZA"), ("Ivy", "Frank Ocean"),
            ("Get You", "Daniel Caesar"),
        ]),
        "top_artists_short": _artists([
            ("Frank Ocean", ["alternative r&b"]), ("Daniel Caesar", ["canadian r&b"]),
            ("SZA", ["r&b"]), ("Childish Gambino", ["hip hop"]),
        ]),
        "top_artists_long": _artists([
            ("Frank Ocean", ["alternative r&b"]), ("SZA", ["r&b"]),
            ("Daniel Caesar", ["canadian r&b"]), ("Steve Lacy", ["alternative r&b"]),
            ("Childish Gambino", ["hip hop"]), ("Brent Faiyaz", ["r&b"]),
            ("Drake", ["rap", "hip hop"]),
        ]),
        "recent": _tracks(
            [("Pink + White", "Frank Ocean")] * 6 + [("Nights", "Frank Ocean")] * 4
            + [("Get You", "Daniel Caesar")] * 3 + [("Snooze", "SZA")] * 2
        ),
    },
    {
        "name": "Maia",
        "top_tracks_short": _tracks([
            ("Espresso", "Sabrina Carpenter"), ("Good Luck, Babe!", "Chappell Roan"),
            ("Pink Pony Club", "Chappell Roan"), ("Apple", "Charli xcx"),
            ("Please Please Please", "Sabrina Carpenter"), ("HOT TO GO!", "Chappell Roan"),
        ]),
        "top_tracks_long": _tracks([
            ("Good Luck, Babe!", "Chappell Roan"), ("Espresso", "Sabrina Carpenter"),
            ("Cruel Summer", "Taylor Swift"), ("360", "Charli xcx"),
        ]),
        "top_artists_short": _artists([
            ("Sabrina Carpenter", ["pop"]), ("Chappell Roan", ["pop"]),
            ("Charli xcx", ["art pop", "hyperpop"]),
        ]),
        "top_artists_long": _artists([
            ("Chappell Roan", ["pop"]), ("Taylor Swift", ["pop"]),
            ("Sabrina Carpenter", ["pop"]), ("Charli xcx", ["art pop", "hyperpop"]),
            ("Olivia Rodrigo", ["pop"]), ("Lorde", ["art pop"]),
            ("Billie Eilish", ["art pop", "pop"]),
        ]),
        "recent": _tracks(
            [("Espresso", "Sabrina Carpenter")] * 9 + [("Apple", "Charli xcx")] * 3
            + [("Pink Pony Club", "Chappell Roan")] * 3
        ),
    },
    {
        "name": "Mia",
        "top_tracks_short": _tracks([
            ("Bags", "Clairo"), ("Sofia", "Clairo"), ("Kyoto", "Phoebe Bridgers"),
            ("Motion Sickness", "Phoebe Bridgers"), ("Juna", "Clairo"),
            ("Seventeen", "Sharon Van Etten"),
        ]),
        "top_tracks_long": _tracks([
            ("Motion Sickness", "Phoebe Bridgers"), ("Bags", "Clairo"),
            ("Kyoto", "Phoebe Bridgers"), ("Not Strong Enough", "boygenius"),
        ]),
        "top_artists_short": _artists([
            ("Clairo", ["bedroom pop", "indie pop"]),
            ("Phoebe Bridgers", ["indie folk"]), ("Sharon Van Etten", ["indie rock"]),
        ]),
        "top_artists_long": _artists([
            ("Phoebe Bridgers", ["indie folk"]), ("Clairo", ["bedroom pop", "indie pop"]),
            ("boygenius", ["indie rock"]), ("Mitski", ["indie rock"]),
            ("Big Thief", ["indie folk"]), ("Faye Webster", ["indie pop"]),
            ("Frank Ocean", ["alternative r&b"]),
        ]),
        "recent": _tracks(
            [("Bags", "Clairo")] * 5 + [("Juna", "Clairo")] * 3
            + [("Kyoto", "Phoebe Bridgers")] * 2 + [("Seventeen", "Sharon Van Etten")] * 2
        ),
    },
    {
        "name": "Kaylie",
        "top_tracks_short": _tracks([
            ("Not Like Us", "Kendrick Lamar"), ("luther", "Kendrick Lamar"),
            ("Money Trees", "Kendrick Lamar"), ("Rich Baby Daddy", "Drake"),
            ("tv off", "Kendrick Lamar"), ("FE!N", "Travis Scott"),
        ]),
        "top_tracks_long": _tracks([
            ("Money Trees", "Kendrick Lamar"), ("Not Like Us", "Kendrick Lamar"),
            ("FE!N", "Travis Scott"), ("Rich Baby Daddy", "Drake"),
        ]),
        "top_artists_short": _artists([
            ("Kendrick Lamar", ["conscious hip hop", "west coast hip hop"]),
            ("Travis Scott", ["rap"]), ("Drake", ["rap", "hip hop"]),
        ]),
        "top_artists_long": _artists([
            ("Kendrick Lamar", ["conscious hip hop", "west coast hip hop"]),
            ("Drake", ["rap", "hip hop"]), ("Travis Scott", ["rap"]),
            ("J. Cole", ["hip hop"]), ("Tyler, The Creator", ["hip hop"]),
            ("Baby Keem", ["rap"]),
        ]),
        "recent": _tracks(
            [("Not Like Us", "Kendrick Lamar")] * 7 + [("luther", "Kendrick Lamar")] * 5
            + [("tv off", "Kendrick Lamar")] * 4 + [("FE!N", "Travis Scott")] * 2
        ),
    },
    {
        "name": "Anjali",
        "top_tracks_short": _tracks([
            ("Die With A Smile", "Lady Gaga"), ("BIRDS OF A FEATHER", "Billie Eilish"),
            ("Saturn", "SZA"), ("Too Sweet", "Hozier"), ("Lunch", "Billie Eilish"),
            ("Beautiful Things", "Benson Boone"),
        ]),
        "top_tracks_long": _tracks([
            ("Heat Waves", "Glass Animals"), ("The Less I Know The Better", "Tame Impala"),
            ("Sweater Weather", "The Neighbourhood"), ("Let It Happen", "Tame Impala"),
        ]),
        "top_artists_short": _artists([
            ("Billie Eilish", ["art pop", "pop"]), ("Hozier", ["irish singer-songwriter"]),
            ("Lady Gaga", ["dance pop"]), ("Benson Boone", ["pop"]),
        ]),
        "top_artists_long": _artists([
            ("Tame Impala", ["neo-psychedelic"]), ("Glass Animals", ["indie rock"]),
            ("The Neighbourhood", ["modern alternative rock"]),
            ("Arctic Monkeys", ["indie rock"]), ("Billie Eilish", ["art pop", "pop"]),
            ("Mac DeMarco", ["indie rock"]), ("SZA", ["r&b"]),
        ]),
        "recent": _tracks(
            [("BIRDS OF A FEATHER", "Billie Eilish")] * 4 + [("Lunch", "Billie Eilish")] * 3
            + [("Too Sweet", "Hozier")] * 3 + [("Die With A Smile", "Lady Gaga")] * 3
        ),
    },
    {
        "name": "Jordan",
        "top_tracks_short": _tracks([
            ("A Bar Song (Tipsy)", "Shaboozey"), ("Lose Control", "Teddy Swims"),
            ("Last Night", "Morgan Wallen"), ("I Had Some Help", "Post Malone"),
            ("Pour Me A Drink", "Post Malone"),
        ]),
        "top_tracks_long": _tracks([
            ("Last Night", "Morgan Wallen"), ("Thinkin' Bout Me", "Morgan Wallen"),
            ("A Bar Song (Tipsy)", "Shaboozey"), ("Fast Car", "Luke Combs"),
        ]),
        "top_artists_short": _artists([
            ("Post Malone", ["pop rap"]), ("Shaboozey", ["country"]),
            ("Morgan Wallen", ["contemporary country"]),
        ]),
        "top_artists_long": _artists([
            ("Morgan Wallen", ["contemporary country"]), ("Luke Combs", ["contemporary country"]),
            ("Zach Bryan", ["classic oklahoma country"]), ("Post Malone", ["pop rap"]),
            ("Shaboozey", ["country"]), ("Noah Kahan", ["pov: indie"]),
            ("Drake", ["rap", "hip hop"]),
        ]),
        "recent": _tracks(
            [("A Bar Song (Tipsy)", "Shaboozey")] * 5 + [("I Had Some Help", "Post Malone")] * 4
            + [("Lose Control", "Teddy Swims")] * 2
        ),
    },
    {
        "name": "Riley",
        "top_tracks_short": _tracks([
            ("Dreams", "Fleetwood Mac"), ("Hey Ya!", "Outkast"), ("Everywhere", "Fleetwood Mac"),
            ("Bohemian Rhapsody", "Queen"), ("Smells Like Teen Spirit", "Nirvana"), ("Go Your Own Way", "Fleetwood Mac"),
        ]),
        "top_tracks_long": _tracks([
            ("Dreams", "Fleetwood Mac"), ("Don't Stop Me Now", "Queen"), ("Hey Ya!", "Outkast"),
            ("I Wanna Dance with Somebody (Who Loves Me)", "Whitney Houston"),
        ]),
        "top_artists_short": _artists([
            ("Fleetwood Mac", ["soft rock", "classic rock"]), ("Outkast", ["southern hip hop"]),
            ("Queen", ["classic rock", "glam rock"]),
        ]),
        "top_artists_long": _artists([
            ("Fleetwood Mac", ["soft rock", "classic rock"]), ("Queen", ["classic rock", "glam rock"]),
            ("Outkast", ["southern hip hop"]), ("Whitney Houston", ["dance pop"]),
            ("Nirvana", ["grunge"]), ("The Beatles", ["classic rock"]),
        ]),
        "recent": _tracks(
            [("Dreams", "Fleetwood Mac")] * 6 + [("Hey Ya!", "Outkast")] * 3
            + [("Bohemian Rhapsody", "Queen")] * 2 + [("Everywhere", "Fleetwood Mac")] * 2
        ),
    },
]


_IMAGES_FILE = __import__("pathlib").Path(__file__).with_name("sample_images.json")
_IMAGES = __import__("json").loads(_IMAGES_FILE.read_text()) if _IMAGES_FILE.exists() else {"tracks": {}, "artists": {}}
# The hour each sample's recent plays happened, newest first. Sam is the
# night owl so the late-night question has someone to be about.
_HOURS = {
    "Sam": [2, 1, 1, 0, 23, 23, 22, 3, 2, 21, 20, 19, 18, 17, 16],
    "Maia": [14, 13, 13, 12, 11, 10, 9, 9, 8, 22, 21, 20, 19, 18, 17],
    "Mia": [23, 22, 22, 21, 20, 1, 19, 18, 17, 16, 15, 14],
    "Kaylie": [18, 17, 17, 16, 15, 15, 14, 13, 12, 11, 10, 9, 8, 8, 7, 7, 6, 6],
    "Anjali": [11, 10, 10, 9, 9, 8, 8, 21, 20, 19, 18, 17, 16],
    "Jordan": [7, 7, 6, 6, 18, 17, 16, 15, 14, 13, 12],
    "Riley": [16, 15, 15, 14, 13, 12, 11, 10, 9, 20, 19, 18, 17],
}


def sample_profile(sample: dict) -> dict:
    """A copy of a sample listener with artwork and play hours filled in."""
    def track(t):
        k = f"{t['name']}|{t['artist']}"
        return {**t, "image": _IMAGES["tracks"].get(k), "year": _IMAGES.get("years", {}).get(k)}

    def artist(a):
        return {**a, "image": _IMAGES["artists"].get(a["name"])}

    hours = _HOURS.get(sample["name"], [])
    recent = [{**track(t), "hour": hours[i] if i < len(hours) else None} for i, t in enumerate(sample["recent"])]
    return {
        "top_tracks_short": [track(t) for t in sample["top_tracks_short"]],
        "top_tracks_long": [track(t) for t in sample["top_tracks_long"]],
        "top_artists_short": [artist(a) for a in sample["top_artists_short"]],
        "top_artists_long": [artist(a) for a in sample["top_artists_long"]],
        "recent": recent,
        "_sample": sample["name"],
    }
