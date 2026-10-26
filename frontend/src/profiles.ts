import { unzipSync, strFromU8 } from "fflate";

export type Track = {
  name: string;
  artist: string;
  image: string | null;
  year: number | null;
  hour?: number | null;
};
export type Artist = { name: string; genres: string[]; image: string | null };
export type Profile = {
  top_tracks_short: Track[];
  top_tracks_long: Track[];
  top_artists_short: Artist[];
  top_artists_long: Artist[];
  recent: Track[];
  self_reported?: boolean;
};
export type Source = "picks" | "export" | "spotify" | "sample" | "statsfm";

/** What a phone keeps between games so the next room is one tap. */
export type Pass = {
  name: string;
  avatar: string | null;
  source: Source;
  profile: Profile;
  saved: number;
  through?: string;
  // stats.fm passes rejoin by username, so every game pulls fresh plays.
  handle?: string;
};

const PASS_KEY = "soundcheck:pass";

export function loadPass(): Pass | null {
  try {
    const raw = localStorage.getItem(PASS_KEY);
    if (!raw) return null;
    const v: unknown = JSON.parse(raw);
    if (
      v &&
      typeof v === "object" &&
      "profile" in v &&
      "name" in v &&
      typeof v.name === "string"
    )
      return v as Pass;
  } catch {
    // Blocked or corrupt storage: start fresh.
  }
  return null;
}

export function savePass(p: Pass) {
  try {
    localStorage.setItem(PASS_KEY, JSON.stringify(p));
  } catch {
    // Storage blocked: the pass lives only for this visit.
  }
}

export function forgetPass() {
  try {
    localStorage.removeItem(PASS_KEY);
  } catch {
    // Nothing to forget.
  }
}

export function passAge(p: Pass): string {
  const days = Math.floor((Date.now() - p.saved) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

export function picksProfile(artists: Artist[], tracks: Track[]): Profile {
  return {
    top_tracks_short: tracks,
    top_tracks_long: tracks,
    top_artists_short: artists,
    top_artists_long: artists,
    recent: [],
    self_reported: true,
  };
}

export async function search(
  q: string,
  kind: "artist" | "track",
): Promise<(Artist | Track)[]> {
  const res = await fetch(`/api/search?${new URLSearchParams({ q, kind })}`);
  if (!res.ok)
    throw new Error(
      res.status === 429 ? "Slow down a sec." : "Search hiccuped. Try again.",
    );
  return (await res.json()) as (Artist | Track)[];
}

/* ------------------------------------------------- Spotify data export -- */

type Play = { at: Date; track: string; artist: string; ms: number };

// A play under 30 seconds is a skip, the same line Spotify uses for streams.
const MIN_MS = 30_000;
const SHORT_DAYS = 28;
const LONG_DAYS = 365;

function readPlays(name: string, text: string): Play[] {
  if (
    !/\.json$/i.test(name) ||
    !/(StreamingHistory|Streaming_History_Audio)/i.test(name)
  )
    return [];
  let rows: unknown;
  try {
    rows = JSON.parse(text);
  } catch {
    return [];
  }
  if (!Array.isArray(rows)) return [];
  const out: Play[] = [];
  for (const r of rows) {
    if (!r || typeof r !== "object") continue;
    const row = r as Record<string, unknown>;
    // Account-data export: endTime "2025-10-01 14:03" (UTC), trackName, artistName, msPlayed.
    // Extended history: ts ISO, master_metadata_track_name, master_metadata_album_artist_name, ms_played.
    const track = (row.trackName ?? row.master_metadata_track_name) as unknown;
    const artist = (row.artistName ??
      row.master_metadata_album_artist_name) as unknown;
    const ms = (row.msPlayed ?? row.ms_played) as unknown;
    const when =
      typeof row.endTime === "string"
        ? `${row.endTime.replace(" ", "T")}:00Z`
        : row.ts;
    if (
      typeof track !== "string" ||
      typeof artist !== "string" ||
      typeof ms !== "number" ||
      typeof when !== "string"
    )
      continue;
    const at = new Date(when);
    if (Number.isNaN(at.getTime()) || ms < MIN_MS) continue;
    out.push({ at, track, artist, ms });
  }
  return out;
}

export async function readExport(files: File[]): Promise<Play[]> {
  const plays: Play[] = [];
  for (const f of files) {
    if (/\.zip$/i.test(f.name)) {
      const entries = unzipSync(new Uint8Array(await f.arrayBuffer()), {
        filter: (e) =>
          /(StreamingHistory|Streaming_History_Audio)[^/]*\.json$/i.test(
            e.name,
          ),
      });
      for (const [name, bytes] of Object.entries(entries))
        plays.push(
          ...readPlays(name.split("/").pop() ?? name, strFromU8(bytes)),
        );
    } else {
      plays.push(...readPlays(f.name, await f.text()));
    }
  }
  return plays.sort((a, b) => b.at.getTime() - a.at.getTime());
}

function topBy<T>(
  plays: Play[],
  key: (p: Play) => string,
  make: (p: Play) => T,
  n: number,
): T[] {
  const ms = new Map<string, { total: number; first: Play }>();
  for (const p of plays) {
    const k = key(p);
    const cur = ms.get(k);
    if (cur) cur.total += p.ms;
    else ms.set(k, { total: p.ms, first: p });
  }
  return [...ms.values()]
    .sort((a, b) => b.total - a.total)
    .slice(0, n)
    .map((v) => make(v.first));
}

/** Summarise the export on the phone. Only this summary ever leaves it. */
export function exportProfile(plays: Play[]): {
  profile: Profile;
  through: string;
} {
  const latest = plays[0]?.at ?? new Date();
  const since = (days: number) =>
    plays.filter((p) => latest.getTime() - p.at.getTime() <= days * 86_400_000);
  const short = since(SHORT_DAYS);
  const long = since(LONG_DAYS);
  const track = (p: Play): Track => ({
    name: p.track,
    artist: p.artist,
    image: null,
    year: null,
  });
  const artist = (p: Play): Artist => ({
    name: p.artist,
    genres: [],
    image: null,
  });
  const keyT = (p: Play) => `${p.track}|${p.artist}`;
  return {
    through: latest.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
    profile: {
      top_tracks_short: topBy(short, keyT, track, 20),
      top_tracks_long: topBy(long, keyT, track, 20),
      top_artists_short: topBy(short, (p) => p.artist, artist, 20),
      top_artists_long: topBy(long, (p) => p.artist, artist, 20),
      recent: plays
        .slice(0, 50)
        .map((p) => ({ ...track(p), hour: p.at.getHours() })),
    },
  };
}

/** Fill album art, artist photos and release years for the items questions use most. */
export async function addArtwork(
  profile: Profile,
  onProgress?: (done: number, total: number) => void,
): Promise<Profile> {
  const tracks = new Map<string, Track>();
  for (const t of [
    ...profile.top_tracks_short.slice(0, 10),
    ...profile.top_tracks_long.slice(0, 10),
    ...profile.recent.slice(0, 3),
  ]) {
    tracks.set(`${t.name}|${t.artist}`, t);
  }
  const artists = new Map<string, Artist>();
  for (const a of [
    ...profile.top_artists_short.slice(0, 8),
    ...profile.top_artists_long.slice(0, 8),
  ])
    artists.set(a.name, a);
  const total = tracks.size + artists.size;
  let done = 0;
  const art = new Map<string, { image: string | null; year: number | null }>();
  const photos = new Map<string, string | null>();
  for (const [k, t] of tracks) {
    try {
      const hit = (
        await search(`track:${t.name} artist:${t.artist}`, "track")
      )[0] as Track | undefined;
      art.set(k, { image: hit?.image ?? null, year: hit?.year ?? null });
    } catch {
      art.set(k, { image: null, year: null });
    }
    onProgress?.(++done, total);
  }
  for (const [name] of artists) {
    try {
      const hit = (await search(name, "artist"))[0] as Artist | undefined;
      photos.set(
        name,
        hit && hit.name.toLowerCase() === name.toLowerCase() ? hit.image : null,
      );
    } catch {
      photos.set(name, null);
    }
    onProgress?.(++done, total);
  }
  const fixT = (t: Track): Track => ({
    ...t,
    ...(art.get(`${t.name}|${t.artist}`) ?? {}),
  });
  const fixA = (a: Artist): Artist => ({
    ...a,
    image: photos.get(a.name) ?? a.image,
  });
  return {
    ...profile,
    top_tracks_short: profile.top_tracks_short.map(fixT),
    top_tracks_long: profile.top_tracks_long.map(fixT),
    top_artists_short: profile.top_artists_short.map(fixA),
    top_artists_long: profile.top_artists_long.map(fixA),
    recent: profile.recent.map(fixT),
  };
}
