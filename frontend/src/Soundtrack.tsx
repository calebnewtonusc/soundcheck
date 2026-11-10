import { useEffect, useRef, useState } from "react";
import {
  api,
  REACTIONS,
  type Option,
  type Player,
  type RoomState,
  type SongCard,
  type Track,
} from "./api";
import { Sidebar, pad } from "./Game";
import { Art, Avatar, Button, Page, Slide, Star } from "./ui";

type Props = {
  state: RoomState;
  isHost: boolean;
  onAnswer: (id: string) => void;
  onPick: (t: Track) => void;
  onNext: () => void;
  onReact: (label: string) => void;
};

const same = (a: Track | null, b: Track) =>
  !!a && a.name === b.name && a.artist === b.artist;

/**
 * Soundtrack: a moment drops, everyone picks a song from their own listening,
 * the room votes on the anonymous picks, then the reveal says whose was whose.
 */
export function SongRound({
  state,
  isHost,
  onAnswer,
  onPick,
  onNext,
  onReact,
}: Props) {
  const q = state.question!;
  const reveal = state.phase === "reveal" ? state.reveal : undefined;
  const step = reveal ? "done" : (q.step ?? "pick");
  const byId = Object.fromEntries(state.players.map((p) => [p.id, p]));
  const judge = q.judge ? byId[q.judge] : undefined;
  const last = q.index + 1 === q.total;

  const [track, setTrack] = useState<Track | null>(null);
  const [vote, setVote] = useState<string | null>(null);
  const key = `${q.index}:${step}`;
  useEffect(() => {
    setTrack(null);
    setVote(null);
  }, [key]);

  const picking = step === "pick" && !q.about_me && !q.my_pick;
  const voting = step === "vote" && !!q.can_vote && !q.my_answer;

  let cta: { label: string; onClick?: () => void; disabled?: boolean };
  if (reveal) {
    cta = isHost
      ? { label: last ? "See the report" : "Next round", onClick: onNext }
      : { label: "Host moves on", disabled: true };
  } else if (picking) {
    cta = {
      label: "Lock in my song",
      disabled: !track,
      onClick: () => {
        if (!track) return;
        navigator.vibrate?.(18);
        onPick(track);
      },
    };
  } else if (voting) {
    cta = {
      label: "Cast my vote",
      disabled: !vote,
      onClick: () => {
        if (!vote) return;
        navigator.vibrate?.(18);
        onAnswer(vote);
      },
    };
  } else if (isHost) {
    cta = {
      label: step === "pick" ? "Close picks, start voting" : "Reveal now",
      onClick: onNext,
    };
  } else {
    cta = {
      label:
        step === "pick"
          ? q.about_me
            ? "They're picking for you"
            : `Locked in, waiting on ${q.waiting_on}`
          : q.can_vote
            ? `Voted, waiting on ${q.waiting_on}`
            : `${judge?.name ?? "The judge"} is deciding`,
      disabled: true,
    };
  }

  return (
    <Page>
      <Slide
        tone="mustard"
        className="flex min-h-[calc(100dvh-24px)] items-center justify-center p-3 pb-32 sm:min-h-[calc(100dvh-48px)] sm:p-[3.5%] lg:px-[6%] lg:pb-[3.5%]"
      >
        <div className="grid w-full overflow-hidden rounded-[22px] bg-app text-paper lg:grid-cols-[minmax(0,1fr)_290px]">
          <div className="halftone flex flex-col gap-6 p-5 sm:gap-7 sm:p-9">
            <div className="flex items-center gap-3 font-mono text-[11px] tracking-[0.08em] text-mute sm:gap-4">
              <span>
                {pad(q.index + 1)} / {pad(q.total)}
              </span>
              <span className="rounded-full bg-mustard px-2.5 py-1 text-ink">
                SOUNDTRACK /{" "}
                {step === "pick" ? "PICK" : step === "vote" ? "VOTE" : "REVEAL"}
              </span>
              <progress
                className="timer flex-1"
                max={q.seconds}
                value={reveal ? 0 : q.time_left}
                aria-label={`${q.time_left} seconds left`}
              />
              <span className="tabular-nums">
                {reveal ? "DONE" : `${pad(q.time_left)}S`}
              </span>
            </div>

            <div key={q.index} className="rise flex items-start gap-5 sm:gap-7">
              {q.image && (
                <Art
                  src={q.image}
                  alt=""
                  className="hidden h-[clamp(96px,11vw,168px)] w-[clamp(96px,11vw,168px)] border-[5px] border-cream sm:block"
                />
              )}
              <div className="min-w-0">
                <h2 className="font-ui text-[clamp(28px,3.9vw,58px)] font-medium leading-[1.03] tracking-[-0.02em]">
                  {q.text}
                </h2>
                {q.hint && (
                  <p className="mt-3 font-mono text-[13px] leading-relaxed text-mustard">
                    {q.hint}
                  </p>
                )}
                {judge && (
                  <p className="mt-3 flex items-center gap-2 font-mono text-[12px] tracking-[0.04em] text-paper/80">
                    <Avatar
                      name={judge.name}
                      src={judge.avatar}
                      className="h-6 w-6 text-[13px]"
                    />
                    {judge.name.toUpperCase()} JUDGES THIS ONE. THEIR VOTE IS
                    WORTH 250.
                  </p>
                )}
              </div>
            </div>

            {step === "pick" &&
              (q.about_me ? (
                <p className="caps flex items-center gap-3 rounded-md bg-mustard px-4 py-3 text-[14px] text-ink">
                  <Star className="h-5 w-5 shrink-0" /> Your friends are picking
                  a song for you. You'll judge.
                </p>
              ) : q.my_pick ? (
                <Locked
                  track={q.my_pick}
                  note="Your pick is in. It stays anonymous until the vote's done."
                />
              ) : (
                <Picker
                  deck={q.deck ?? []}
                  selected={track}
                  onSelect={setTrack}
                />
              ))}

            {step === "vote" && (
              <Ballot
                options={q.options}
                selected={q.my_answer ?? vote}
                onSelect={setVote}
                enabled={voting}
                note={
                  q.can_vote
                    ? "Whose is whose stays hidden. Vote for the song that fits the moment, not your friend."
                    : `${judge?.name ?? "The judge"} is choosing. Keep a straight face if one's yours.`
                }
              />
            )}

            {reveal?.song && (
              <Reveal
                key={q.index}
                cards={reveal.song.cards}
                byId={byId}
                players={state.players}
                missed={reveal.song.missed}
                reactions={reveal.reactions}
                me={state.me}
                onReact={onReact}
              />
            )}
          </div>

          <Sidebar state={state} category="soundtrack" cta={cta} />
        </div>
      </Slide>
      <div className="pointer-events-none fixed inset-x-3 bottom-3 z-30 lg:hidden">
        <Button
          onClick={cta.onClick}
          disabled={cta.disabled}
          className="pointer-events-auto min-h-14 w-full disabled:bg-tile disabled:text-paper/70 disabled:opacity-100"
        >
          {cta.label} <span aria-hidden>&rarr;</span>
        </Button>
      </div>
    </Page>
  );
}

function SongTile({
  t,
  selected,
  disabled,
  onClick,
  tag,
}: {
  t: Track;
  selected: boolean;
  disabled?: boolean;
  onClick?: () => void;
  tag?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
      className={`press flex w-full items-center gap-3 rounded-[3px] border p-2.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream disabled:cursor-default ${
        selected
          ? "border-mustard bg-tile-up"
          : "border-line bg-tile enabled:hover:border-mute"
      } ${disabled && !selected ? "opacity-60" : ""}`}
    >
      <Art src={t.image} alt="" className="h-14 w-14" />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-ui text-[16px] font-medium leading-tight">
          {t.name}
        </span>
        <span className="truncate font-mono text-[12px] opacity-70">
          {t.artist}
        </span>
      </span>
      {tag && (
        <span className="shrink-0 rounded-full border border-line px-2 py-0.5 font-mono text-[10px] text-mute">
          {tag}
        </span>
      )}
      {selected && <Star className="h-5 w-5 shrink-0 text-mustard" />}
    </button>
  );
}

function Picker({
  deck,
  selected,
  onSelect,
}: {
  deck: Track[];
  selected: Track | null;
  onSelect: (t: Track) => void;
}) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Track[]>([]);
  const [searched, setSearched] = useState("");
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    window.clearTimeout(timer.current);
    const q = query.trim();
    if (q.length < 2) {
      setHits([]);
      setError("");
      setSearched("");
      return;
    }
    timer.current = window.setTimeout(async () => {
      setSearching(true);
      try {
        setHits(await api.searchTracks(q));
        setError("");
      } catch (e) {
        setHits([]);
        setError(
          e instanceof Error
            ? e.message
            : "Search didn't work. Pick from your songs.",
        );
      } finally {
        setSearching(false);
        setSearched(q);
      }
    }, 300);
    return () => window.clearTimeout(timer.current);
  }, [query]);

  // "Nothing found" only once a search for exactly this text has come back.
  const empty =
    !searching &&
    !error &&
    searched !== "" &&
    searched === query.trim() &&
    hits.length === 0;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="mb-2 font-mono text-[11px] tracking-[0.08em] text-mute">
          FROM YOUR LISTENING
        </p>
        {deck.length ? (
          <ul className="grid gap-2 sm:grid-cols-2" aria-label="Your top songs">
            {deck.map((t) => (
              <li key={`${t.name}|${t.artist}`}>
                <SongTile
                  t={t}
                  selected={same(selected, t)}
                  onClick={() => onSelect(t)}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="font-mono text-[12px] text-paper/70">
            No songs on file for you yet. Search for one below.
          </p>
        )}
      </div>
      <div>
        <label
          htmlFor="song-search"
          className="mb-2 block font-mono text-[11px] tracking-[0.08em] text-mute"
        >
          OR FIND ANY SONG
        </label>
        <input
          id="song-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search Spotify"
          autoComplete="off"
          className="w-full rounded-[3px] border border-line bg-tile px-4 py-3 font-ui text-[16px] text-paper placeholder:text-mute hover:border-mute focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream"
        />
        {searching && (
          <p className="mt-2 font-mono text-[11px] text-mute">Searching...</p>
        )}
        {error && (
          <p className="mt-2 font-mono text-[12px] text-mustard">{error}</p>
        )}
        {empty && (
          <p className="mt-2 font-mono text-[12px] text-paper/70">
            Nothing found. Try the artist's name too.
          </p>
        )}
        {hits.length > 0 && (
          <ul
            className="mt-2 grid gap-2 sm:grid-cols-2"
            aria-label="Search results"
          >
            {hits.map((t) => (
              <li key={`${t.id ?? t.name}|${t.artist}`}>
                <SongTile
                  t={t}
                  selected={same(selected, t)}
                  onClick={() => onSelect(t)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Locked({ track, note }: { track: Track; note: string }) {
  return (
    <div className="rise flex flex-col gap-3">
      <SongTile t={track} selected disabled />
      <p className="font-mono text-[12px] leading-relaxed text-paper/75">
        {note}
      </p>
    </div>
  );
}

function Ballot({
  options,
  selected,
  onSelect,
  enabled,
  note,
}: {
  options: Option[];
  selected: string | null;
  onSelect: (id: string) => void;
  enabled: boolean;
  note: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      <p className="font-mono text-[12px] leading-relaxed text-paper/75">
        {note}
      </p>
      <ul
        className="grid gap-2 sm:grid-cols-2"
        aria-label="Vote for the best pick"
      >
        {options.map((o) => (
          <li key={o.id}>
            <SongTile
              t={{ name: o.label, artist: o.sub, image: o.image }}
              selected={selected === o.id}
              disabled={!enabled || o.mine}
              onClick={() => onSelect(o.id)}
              tag={o.mine ? "YOURS" : undefined}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

function Reveal({
  cards,
  byId,
  players,
  missed,
  reactions,
  me,
  onReact,
}: {
  cards: SongCard[];
  byId: Record<string, Player>;
  players: Player[];
  missed: string[];
  reactions: [string, string][];
  me: string | null;
  onReact: (label: string) => void;
}) {
  const [playing, setPlaying] = useState<string | null>(
    cards.find((c) => c.winner && c.track_id)?.id ?? null,
  );
  if (!cards.length)
    return (
      <p className="rise font-mono text-[13px] text-paper/80">
        Nobody locked in a song this round. On to the next one.
      </p>
    );
  const idx = (pid: string) => players.findIndex((p) => p.id === pid);
  return (
    <div className="rise flex flex-col gap-4">
      <ol
        className="flex flex-col gap-3"
        aria-label="The picks, most votes first"
      >
        {cards.map((c) => {
          const owner = byId[c.owner];
          return (
            <li
              key={c.id}
              className={`rounded-[4px] border p-3 sm:p-4 ${c.winner ? "border-mustard bg-tile-up" : "border-line bg-tile"}`}
            >
              <div className="flex items-center gap-3">
                <Art
                  src={c.image ?? null}
                  alt=""
                  className="h-16 w-16 sm:h-20 sm:w-20"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-ui text-[17px] font-medium leading-tight sm:text-[20px]">
                    {c.label}
                  </p>
                  <p className="truncate font-mono text-[12px] opacity-70">
                    {c.sub}
                  </p>
                  <p className="mt-1.5 flex items-center gap-2 font-mono text-[12px] tracking-[0.02em]">
                    {owner && (
                      <Avatar
                        name={owner.name}
                        src={owner.avatar}
                        index={idx(owner.id)}
                        className="h-5 w-5 text-[11px]"
                      />
                    )}
                    <span className="uppercase">
                      {owner?.name ?? "Someone"}'s pick
                    </span>
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1 font-mono">
                  {c.winner && <Star className="h-6 w-6 text-mustard" />}
                  <span className="text-[20px] tabular-nums">{c.votes}</span>
                  <span className="text-[10px] tracking-[0.06em] text-mute">
                    {c.votes === 1 ? "VOTE" : "VOTES"}
                  </span>
                  {c.points > 0 && (
                    <span className="text-[12px] text-gain">+{c.points}</span>
                  )}
                </div>
              </div>
              {(c.voters.length > 0 || c.notes.length > 0) && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {c.voters.length > 0 && (
                    <span className="rounded-full border border-line px-2.5 py-1 font-mono text-[11px] text-paper/80">
                      Votes:{" "}
                      {c.voters.map((v) => byId[v]?.name ?? "?").join(", ")}
                    </span>
                  )}
                  {c.notes.map((n) => (
                    <span
                      key={n}
                      className="rounded-full bg-mustard px-2.5 py-1 font-mono text-[11px] text-ink"
                    >
                      {n}
                    </span>
                  ))}
                </div>
              )}
              {c.track_id &&
                (playing === c.id ? (
                  <iframe
                    title={`${c.label} by ${c.sub}`}
                    src={`https://open.spotify.com/embed/track/${c.track_id}?theme=0`}
                    className="mt-3 h-[80px] w-full rounded-[12px]"
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    loading="lazy"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => setPlaying(c.id)}
                    className="press mt-3 rounded-full border border-line px-3.5 py-1.5 font-mono text-[12px] text-paper/85 hover:border-mute focus-visible:outline-2 focus-visible:outline-cream"
                  >
                    Play it
                  </button>
                ))}
            </li>
          );
        })}
      </ol>
      {missed.length > 0 && (
        <p className="font-mono text-[11px] text-mute">
          Didn't pick in time:{" "}
          {missed.map((m) => byId[m]?.name ?? "?").join(", ")}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2" aria-label="React">
        <span className="mr-1 font-mono text-[11px] tracking-[0.08em] text-mute">
          DEBATE IT
        </span>
        {REACTIONS.map((label) => {
          const who = reactions.filter(([, l]) => l === label);
          const mine = reactions.some(([pid, l]) => pid === me && l === label);
          return (
            <button
              key={label}
              type="button"
              onClick={() => onReact(label)}
              aria-pressed={mine}
              className={`press rounded-full border px-3.5 py-1.5 font-mono text-[12px] tracking-[0.04em] focus-visible:outline-2 focus-visible:outline-cream ${
                mine
                  ? "border-cream bg-cream text-app"
                  : "border-line text-paper/80 hover:border-mute"
              }`}
            >
              {label}
              {who.length ? ` ${who.length}` : ""}
            </button>
          );
        })}
      </div>
    </div>
  );
}
