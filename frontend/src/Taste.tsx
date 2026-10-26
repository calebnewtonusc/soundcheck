import { useEffect, useRef, useState } from "react";
import {
  addArtwork,
  exportProfile,
  picksProfile,
  readExport,
  search,
  type Artist,
  type Profile,
  type Source,
  type Track,
} from "./profiles";
import { Art, Button, Star } from "./ui";

// Three is the fewest that still makes a question; five keeps it a minute.
const MIN_PICKS = 3;
const MAX_PICKS = 5;

export type TasteResult = {
  source: Source;
  profile: Profile;
  through?: string;
};

/** Build a taste profile from quick picks or a Spotify data export. */
export function TasteBuilder({
  kind,
  onDone,
  onCancel,
}: {
  kind: "picks" | "export";
  onDone: (r: TasteResult) => void;
  onCancel: () => void;
}) {
  return kind === "picks" ? <Picks onDone={onDone} onCancel={onCancel} /> : <Upload onDone={onDone} onCancel={onCancel} />;
}

function Picks({
  onDone,
  onCancel,
}: {
  onDone: (r: TasteResult) => void;
  onCancel: () => void;
}) {
  const [artists, setArtists] = useState<Artist[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [kind, setKind] = useState<"artist" | "track">("artist");
  const setForceTracks = (tracksTab: boolean) => setKind(tracksTab ? "track" : "artist");
  const ready = artists.length >= MIN_PICKS && tracks.length >= MIN_PICKS;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex gap-2">
        <StepTab
          on={kind === "artist"}
          onClick={() => setForceTracks(false)}
          count={artists.length}
          label="Top artists"
        />
        <StepTab
          on={kind === "track"}
          onClick={() => setForceTracks(true)}
          count={tracks.length}
          label="On repeat"
        />
      </div>
      <p className="caps text-[14px] leading-snug opacity-90">
        {kind === "artist"
          ? "Who are you listening to most right now? Pick 3 to 5."
          : "Which songs are on repeat right now? Pick 3 to 5."}
      </p>
      <SearchBox
        key={kind}
        kind={kind}
        taken={
          kind === "artist"
            ? artists.map((a) => a.name)
            : tracks.map((t) => `${t.name}|${t.artist}`)
        }
        full={(kind === "artist" ? artists : tracks).length >= MAX_PICKS}
        onPick={(item) => {
          if (kind === "artist") {
            const next = [...artists, item as Artist];
            setArtists(next);
            if (next.length >= MAX_PICKS) setForceTracks(true);
          } else {
            setTracks([...tracks, item as Track]);
          }
        }}
      />
      <ul className="flex flex-wrap gap-2" aria-label="Your picks">
        {(kind === "artist" ? artists : tracks).map((item, i) => (
          <li
            key={i}
            className="flex items-center gap-2 rounded-full bg-cream/15 py-1 pl-1 pr-3"
          >
            <Art
              src={item.image}
              alt=""
              round={kind === "artist"}
              className="h-8 w-8"
            />
            <span className="max-w-[180px] truncate text-[14px]">
              {item.name}
            </span>
            <button
              type="button"
              aria-label={`Remove ${item.name}`}
              onClick={() =>
                kind === "artist"
                  ? setArtists(artists.filter((_, j) => j !== i))
                  : setTracks(tracks.filter((_, j) => j !== i))
              }
              className="press font-mono text-[16px] opacity-70 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
            >
              &times;
            </button>
          </li>
        ))}
      </ul>
      <div className="flex flex-col gap-3 sm:flex-row">
        {kind === "artist" && artists.length >= MIN_PICKS ? (
          <Button
            type="button"
            onClick={() => setForceTracks(true)}
            className="sm:flex-1"
          >
            Next: songs
          </Button>
        ) : (
          <Button
            type="button"
            disabled={!ready}
            onClick={() =>
              onDone({
                source: "picks",
                profile: picksProfile(artists, tracks),
              })
            }
            className="sm:flex-1"
          >
            {ready
              ? "Lock in my taste"
              : `Pick ${Math.max(0, MIN_PICKS - tracks.length)} more`}
          </Button>
        )}
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          className="sm:flex-1"
        >
          Back
        </Button>
      </div>
    </div>
  );
}


function StepTab({
  on,
  onClick,
  count,
  label,
}: {
  on: boolean;
  onClick: () => void;
  count: number;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={`press caps flex-1 rounded-md border-2 px-3 py-2 text-[13px] focus-visible:outline-2 focus-visible:outline-cream ${on ? "border-cream bg-cream text-red" : "border-cream/40 hover:border-cream"}`}
    >
      {label}{" "}
      <span className="font-mono">
        {count}/{MAX_PICKS}
      </span>
    </button>
  );
}

function SearchBox({
  kind,
  taken,
  full,
  onPick,
}: {
  kind: "artist" | "track";
  taken: string[];
  full: boolean;
  onPick: (x: Artist | Track) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<(Artist | Track)[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "empty">(
    "idle",
  );
  const timer = useRef<number>(0);

  useEffect(() => {
    window.clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults([]);
      setStatus("idle");
      return;
    }
    // Wait for a pause in typing: one search per word, not per letter.
    timer.current = window.setTimeout(async () => {
      setStatus("loading");
      try {
        const r = await search(q.trim(), kind);
        setResults(r);
        setStatus(r.length ? "idle" : "empty");
      } catch {
        setStatus("error");
      }
    }, 280);
    return () => window.clearTimeout(timer.current);
  }, [q, kind]);

  const keyOf = (x: Artist | Track) =>
    "artist" in x ? `${x.name}|${x.artist}` : x.name;

  return (
    <div className="flex flex-col gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        disabled={full}
        placeholder={
          full
            ? "That's 5. Remove one to swap."
            : kind === "artist"
              ? "Search artists"
              : "Search songs"
        }
        className="caps rounded-md border-2 border-cream/60 bg-transparent px-4 py-3 text-[16px] text-cream placeholder:text-cream/50 focus-visible:border-cream focus-visible:outline-1 focus-visible:outline-offset-4 focus-visible:outline-cream/40 disabled:opacity-60"
        aria-label={kind === "artist" ? "Search artists" : "Search songs"}
      />
      {status === "loading" && (
        <p className="font-mono text-[12px] opacity-75">Searching Spotify...</p>
      )}
      {status === "empty" && (
        <p className="font-mono text-[12px] opacity-75">
          Nothing for that. Try another spelling.
        </p>
      )}
      {status === "error" && (
        <p className="font-mono text-[12px] opacity-75">
          Search hiccuped. Type again in a sec.
        </p>
      )}
      {results.length > 0 && !full && (
        <ul className="max-h-[260px] overflow-y-auto rounded-md bg-ink/30">
          {results.map((r) => {
            const isTaken = taken.includes(keyOf(r));
            return (
              <li key={keyOf(r)}>
                <button
                  type="button"
                  disabled={isTaken}
                  onClick={() => {
                    onPick(r);
                    setQ("");
                  }}
                  className="press flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-cream/10 focus-visible:outline-2 focus-visible:outline-cream disabled:opacity-40"
                >
                  <Art
                    src={r.image}
                    alt=""
                    round={kind === "artist"}
                    className="h-10 w-10"
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-[15px]">{r.name}</span>
                    {"artist" in r && (
                      <span className="block truncate font-mono text-[12px] opacity-70">
                        {r.artist}
                        {r.year ? ` / ${r.year}` : ""}
                      </span>
                    )}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Upload({
  onDone,
  onCancel,
}: {
  onDone: (r: TasteResult) => void;
  onCancel: () => void;
}) {
  const [status, setStatus] = useState<{
    step: "idle" | "reading" | "art" | "error";
    note: string;
  }>({ step: "idle", note: "" });

  async function handle(files: FileList | null) {
    if (!files?.length) return;
    setStatus({
      step: "reading",
      note: "Reading your listening history on this phone",
    });
    try {
      const plays = await readExport([...files]);
      if (plays.length < 50) {
        setStatus({
          step: "error",
          note: "Couldn't find listening history in that file. Upload the zip Spotify emailed you, or the StreamingHistory files inside it.",
        });
        return;
      }
      const { profile, through } = exportProfile(plays);
      setStatus({
        step: "art",
        note: `${plays.length.toLocaleString()} plays read. Adding album art`,
      });
      const withArt = await addArtwork(profile, (d, t) =>
        setStatus({
          step: "art",
          note: `${plays.length.toLocaleString()} plays read. Adding album art ${d}/${t}`,
        }),
      );
      onDone({ source: "export", profile: withArt, through });
    } catch {
      setStatus({
        step: "error",
        note: "That file didn't open. Try the zip again, or unzip it and pick the StreamingHistory files.",
      });
    }
  }

  const busy = status.step === "reading" || status.step === "art";
  return (
    <div className="flex flex-col gap-5">
      <ol className="flex flex-col gap-3 text-[15px] leading-snug">
        <li className="flex gap-3">
          <span className="font-cond text-[22px] leading-none">1</span>
          <span>
            Open{" "}
            <a
              href="https://www.spotify.com/account/privacy/"
              target="_blank"
              rel="noreferrer"
              className="underline underline-offset-4 hover:opacity-80 focus-visible:outline-2 focus-visible:outline-cream"
            >
              Spotify privacy settings
            </a>{" "}
            and request <span className="caps">Account data</span>. Spotify
            emails it, usually within 5 days.
          </span>
        </li>
        <li className="flex gap-3">
          <span className="font-cond text-[22px] leading-none">2</span>
          <span>
            Upload the zip here. It's read on this phone. Only your top songs,
            top artists and last 50 plays go to the room.
          </span>
        </li>
      </ol>
      <label
        className={`press caps flex min-h-14 cursor-pointer items-center justify-center gap-3 rounded-full bg-cream px-7 text-[15px] text-ink hover:bg-paper focus-within:outline-2 focus-within:outline-offset-4 focus-within:outline-cream ${busy ? "pointer-events-none opacity-60" : ""}`}
      >
        {busy ? <Star className="spin-slow h-5 w-5" /> : null}
        {busy ? "Working" : "Upload my Spotify data"}
        <input
          type="file"
          accept=".zip,.json,application/zip,application/json"
          multiple
          className="sr-only"
          onChange={(e) => handle(e.target.files)}
        />
      </label>
      {status.note && (
        <p
          className={`font-mono text-[12px] leading-relaxed ${status.step === "error" ? "" : "opacity-80"}`}
        >
          {status.note}
        </p>
      )}
      <Button type="button" variant="ghost" onClick={onCancel} disabled={busy}>
        Back
      </Button>
    </div>
  );
}
