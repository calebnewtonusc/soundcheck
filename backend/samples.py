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
            ("Mac DeMarco", ["indie rock"]),
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
        ]),
        "recent": _tracks(
            [("A Bar Song (Tipsy)", "Shaboozey")] * 5 + [("I Had Some Help", "Post Malone")] * 4
            + [("Lose Control", "Teddy Swims")] * 2
        ),
    },
]
