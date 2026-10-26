import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { api, loadCreds, saveCreds, type Creds, type RoomState } from "./api";
import { go } from "./App";
import {
  Arrow,
  Bubble,
  Button,
  Page,
  Slide,
  Star,
  Toast,
  Wordmark,
} from "./ui";

const POLL_MS = 1000;
const pad = (n: number) => String(n).padStart(2, "0");

export function Room({ code }: { code: string }) {
  const [creds, setCreds] = useState<Creds | null>(() => loadCreds(code));
  const [state, setState] = useState<RoomState | null>(null);
  const [missing, setMissing] = useState(false);
  const [offline, setOffline] = useState(false);
  const [error, setError] = useState("");

  // Coming back from Spotify: pick creds or an error off the URL, then clean it.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const pid = q.get("pid");
    const key = q.get("key");
    if (pid && key) {
      saveCreds(code, { pid, key });
      setCreds({ pid, key });
    }
    const err = q.get("error");
    if (err) setError(err);
    if (q.toString()) window.history.replaceState({}, "", `/room/${code}`);
  }, [code]);

  const refresh = useCallback(async () => {
    try {
      setState(await api.state(code, creds));
      setMissing(false);
      setOffline(false);
    } catch (e) {
      if (e instanceof Error && e.message.startsWith("No room"))
        setMissing(true);
      else setOffline(true);
    }
  }, [code, creds]);

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(t);
  }, [refresh]);

  const act = async (fn: () => Promise<RoomState>) => {
    try {
      setState(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    }
  };

  const toast = error ? (
    <Toast message={error} onClose={() => setError("")} />
  ) : offline && state ? (
    <Toast
      message="Lost the room for a sec. Reconnecting."
      onClose={() => setOffline(false)}
    />
  ) : null;

  if (missing) {
    return (
      <Page>
        <Slide
          tone="red"
          className="flex min-h-[calc(100dvh-24px)] flex-col items-center justify-center gap-8 px-6 text-center sm:min-h-[calc(100dvh-48px)]"
        >
          <p className="display text-[clamp(40px,8vw,120px)]">No room {code}</p>
          <p className="caps text-[clamp(16px,2vw,26px)]">
            That code doesn't match an open room. It might have ended.
          </p>
          <Button onClick={() => go("/")}>Back to start</Button>
        </Slide>
      </Page>
    );
  }

  if (!state) {
    return (
      <Page>
        <Slide
          tone="blue"
          className="flex min-h-[calc(100dvh-24px)] flex-col items-center justify-center gap-6 sm:min-h-[calc(100dvh-48px)]"
        >
          <Star className="spin-slow h-20 w-20 text-cream" />
          <p className="caps text-[16px]">
            {offline
              ? "Can't reach the room. Retrying."
              : `Opening room ${code}`}
          </p>
        </Slide>
      </Page>
    );
  }

  const me = state.me;
  if (!me || !creds) {
    return (
      <>
        {toast}
        <Join
          code={code}
          state={state}
          onJoined={(c) => (saveCreds(code, c), setCreds(c))}
          onError={setError}
        />
      </>
    );
  }

  const isHost = state.host_id === me;
  return (
    <>
      {toast}
      {state.phase === "lobby" && (
        <Lobby
          state={state}
          isHost={isHost}
          onBots={() => act(() => api.bots(code, creds))}
          onStart={() => act(() => api.start(code, creds))}
        />
      )}
      {(state.phase === "question" || state.phase === "reveal") && (
        <Game
          state={state}
          isHost={isHost}
          onAnswer={(id) => act(() => api.answer(code, creds, id))}
          onNext={() => act(() => api.next(code, creds))}
        />
      )}
      {state.phase === "report" && (
        <Report
          state={state}
          isHost={isHost}
          onRematch={() => act(() => api.rematch(code, creds))}
        />
      )}
    </>
  );
}

/* ------------------------------------------------------------------ join */

function Join({
  code,
  state,
  onJoined,
  onError,
}: {
  code: string;
  state: RoomState;
  onJoined: (c: Creds) => void;
  onError: (m: string) => void;
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [spotifyOn, setSpotifyOn] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.health().then(
      (h) => setSpotifyOn(h.spotify),
      () => setSpotifyOn(false),
    );
    inputRef.current?.focus();
  }, []);

  const started = state.phase !== "lobby";
  const ready = name.trim().length > 0 && !busy && !started;

  function spotify(e: FormEvent) {
    e.preventDefault();
    if (!ready) return;
    setBusy(true);
    window.location.href = api.loginUrl(code, name.trim());
  }

  async function sample() {
    if (!ready) return;
    setBusy(true);
    try {
      onJoined(await api.joinSample(code, name.trim()));
    } catch (e) {
      onError(e instanceof Error ? e.message : "Couldn't join.");
      setBusy(false);
    }
  }

  return (
    <Page>
      <Slide
        tone="red"
        className="flex min-h-[calc(100dvh-24px)] flex-col justify-center px-6 py-16 sm:min-h-[calc(100dvh-48px)] sm:px-[10%]"
      >
        <div className="rise flex flex-col gap-10 lg:flex-row lg:items-center lg:justify-between lg:gap-16">
          <div>
            <p className="caps text-[clamp(14px,1.5vw,20px)] opacity-80">
              Room
            </p>
            <p className="display text-[clamp(64px,9vw,150px)] tracking-[0.04em]">
              {code}
            </p>
            <p className="caps mt-3 text-[clamp(15px,1.6vw,22px)]">
              {state.players.length === 0
                ? "You're first in."
                : `${state.players.map((p) => p.name).join(", ")} ${state.players.length === 1 ? "is" : "are"} already here.`}
            </p>
          </div>

          <form
            onSubmit={spotify}
            className="flex w-full min-w-0 max-w-lg flex-col gap-6 lg:shrink-0"
          >
            <Wordmark stacked className="text-[clamp(44px,5vw,76px)]" />
            <label className="caps flex flex-col gap-2 text-[14px]">
              <span className="opacity-80">
                1 &nbsp;What do your friends call you?
              </span>
              <input
                ref={inputRef}
                value={name}
                onChange={(e) => setName(e.target.value.slice(0, 20))}
                placeholder="YOUR NAME"
                autoComplete="given-name"
                className="caps rounded-sm border-b-[3px] border-cream/70 bg-transparent pb-2 text-[clamp(26px,3vw,40px)] text-cream placeholder:text-cream/40 focus-visible:border-cream focus-visible:outline-1 focus-visible:outline-offset-8 focus-visible:outline-cream/40"
              />
            </label>
            <span className="caps -mb-3 text-[14px] opacity-80">
              2 &nbsp;Bring your listening history
            </span>
            {started ? (
              <p className="caps text-[18px]">
                This game already started. Hang tight for the rematch.
              </p>
            ) : (
              <div className="flex flex-col gap-3 sm:flex-row">
                {spotifyOn && (
                  <Button type="submit" disabled={!ready} className="sm:flex-1">
                    {busy ? "Opening Spotify" : "Connect Spotify"}
                  </Button>
                )}
                <Button
                  type="button"
                  variant={spotifyOn ? "ghost" : "solid"}
                  disabled={!ready}
                  onClick={sample}
                  className="sm:flex-1"
                >
                  Sample profile
                </Button>
              </div>
            )}
            <p className="font-mono text-[12px] leading-relaxed opacity-75">
              We read your top tracks, top artists and last 50 plays once, to
              write the questions. Your Spotify login is never stored.
            </p>
          </form>
        </div>
      </Slide>
    </Page>
  );
}

/* ----------------------------------------------------------------- lobby */

function sourceLine(p: RoomState["players"][number]) {
  if (p.bot) return "Demo friend";
  return p.source === "spotify" ? "Spotify connected" : "Sample listener";
}

function Lobby({
  state,
  isHost,
  onBots,
  onStart,
}: {
  state: RoomState;
  isHost: boolean;
  onBots: () => void;
  onStart: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const host = state.players.find((p) => p.id === state.host_id);
  const link = `${window.location.origin}/room/${state.code}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Page>
      <Slide
        tone="green"
        className="min-h-[calc(100dvh-24px)] px-6 pb-24 pt-12 sm:min-h-[calc(100dvh-48px)] sm:px-[7%] sm:pt-16"
      >
        <h2 className="display text-center text-[clamp(28px,4.2vw,72px)]">
          Put your friends taste
          <br />
          to the test
        </h2>

        <div className="mt-12 grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div className="flex flex-col gap-6">
            <div>
              <p className="caps text-[15px] opacity-80">Room code</p>
              <p className="display text-[clamp(64px,7.4vw,124px)] tracking-[0.04em]">
                {state.code}
              </p>
            </div>
            <Button variant="ghost" onClick={copy} className="self-start">
              {copied ? "Link copied" : "Copy invite link"}
            </Button>
            <p className="caps text-[clamp(15px,1.5vw,20px)] leading-snug opacity-90">
              {state.players.length} in the room.{" "}
              {state.players.length < 2
                ? "Need at least 2 to play."
                : "Enough to start."}
            </p>
            {isHost ? (
              <div className="flex flex-col gap-3 sm:flex-row lg:flex-col xl:flex-row">
                <Button onClick={onStart} disabled={state.players.length < 2}>
                  Start the quiz
                </Button>
                <Button variant="ghost" onClick={onBots}>
                  Add demo friends
                </Button>
              </div>
            ) : (
              <p className="caps text-[18px]">
                Waiting for {host?.name ?? "the host"} to start.
              </p>
            )}
          </div>

          <ul className="flex flex-col gap-14 pb-6" aria-label="Players">
            {state.players.map((p, i) => (
              <li key={p.id} className="rise flex flex-col">
                <Bubble side={i % 2 ? "right" : "left"} filled={i % 2 === 1}>
                  &ldquo;{p.name} is in.&rdquo;
                  <span className="mt-1 block font-mono text-[12px] normal-case tracking-[0.04em] opacity-75">
                    {sourceLine(p)}
                    {p.id === state.host_id ? " / host" : ""}
                    {p.id === state.me ? " / you" : ""}
                  </span>
                </Bubble>
              </li>
            ))}
          </ul>
        </div>
      </Slide>
    </Page>
  );
}

/* ------------------------------------------------------------------ game */

const STEPS: { id: string; label: string }[] = [
  { id: "songs", label: "Top songs" },
  { id: "artists", label: "Top artists" },
  { id: "genre", label: "Top genre" },
  { id: "report", label: "Report" },
];

function Game({
  state,
  isHost,
  onAnswer,
  onNext,
}: {
  state: RoomState;
  isHost: boolean;
  onAnswer: (id: string) => void;
  onNext: () => void;
}) {
  const q = state.question;
  const [picked, setPicked] = useState<string | null>(null);
  const index = q?.index;
  useEffect(() => setPicked(null), [index]);
  if (!q) return null;

  const reveal = state.phase === "reveal" ? state.reveal : undefined;
  const locked = q.my_answer ?? null;
  const selected = locked ?? picked;
  const total = state.players.length;
  const answered = state.players.filter((p) => p.answered).length;
  const byId = Object.fromEntries(state.players.map((p) => [p.id, p]));
  const last = q.index + 1 === q.total;

  let cta: { label: string; onClick?: () => void; disabled?: boolean };
  if (reveal) {
    cta = isHost
      ? { label: last ? "See the report" : "Next question", onClick: onNext }
      : { label: "Host moves on", disabled: true };
  } else if (q.about_me || locked) {
    cta = isHost
      ? { label: "Reveal now", onClick: onNext }
      : { label: q.about_me ? "It's about you" : "Locked in", disabled: true };
  } else {
    cta = {
      label: "Lock it in",
      onClick: () => picked && onAnswer(picked),
      disabled: !picked,
    };
  }

  return (
    <Page>
      <Slide
        tone="blue"
        className="flex min-h-[calc(100dvh-24px)] items-center justify-center p-3 pb-20 sm:min-h-[calc(100dvh-48px)] sm:p-[4%] sm:pb-[6%] lg:px-[9%]"
      >
        <div className="grid w-full overflow-hidden rounded-[22px] bg-app text-paper lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="halftone flex flex-col gap-7 p-5 sm:p-9">
            <progress
              className="timer"
              max={q.seconds}
              value={reveal ? 0 : q.time_left}
              aria-label={`${q.time_left} seconds left`}
            />
            <h2
              key={q.index}
              className="rise font-ui text-[clamp(30px,4.4vw,64px)] font-medium leading-[1.02] tracking-[-0.02em]"
            >
              {q.text}
            </h2>

            {q.about_me && !reveal && (
              <p className="caps flex items-center gap-3 rounded-md bg-mustard px-4 py-3 text-[14px] text-ink">
                <Star className="h-5 w-5 shrink-0" /> This one's about you. Keep
                a straight face.
              </p>
            )}

            <ul
              className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3"
              aria-label="Who is it?"
            >
              {state.players.map((p, i) => {
                const right = reveal?.correct.includes(p.id);
                const pickers = reveal
                  ? Object.entries(reveal.picks)
                      .filter(([, c]) => c === p.id)
                      .map(([pid]) => byId[pid]?.name)
                  : [];
                const pts = reveal?.points[p.id];
                const isSel = selected === p.id;
                const disabled = !!reveal || !!locked || q.about_me;
                const tone = reveal
                  ? right
                    ? "border-cream bg-cream text-app"
                    : "border-line bg-tile text-paper/45"
                  : isSel
                    ? "border-paper bg-tile text-paper"
                    : "border-line bg-tile text-paper hover:border-mute";
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => setPicked(p.id)}
                      aria-pressed={isSel}
                      className={`press flex h-full min-h-[132px] w-full flex-col justify-between rounded-[3px] border p-4 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream disabled:cursor-default sm:min-h-[168px] sm:p-5 ${tone}`}
                    >
                      <span className="flex items-center justify-between font-mono text-[11px] tracking-[0.06em] sm:text-[12px]">
                        {pad(i + 1)} / {pad(total)}
                        {reveal && right && (
                          <Star className="h-5 w-5 text-red" />
                        )}
                        {!reveal && p.answered && (
                          <span className="opacity-70">in</span>
                        )}
                      </span>
                      <span className="mt-4 font-ui text-[clamp(17px,1.8vw,24px)] font-medium uppercase tracking-[0.01em]">
                        {p.name}
                      </span>
                      <span className="mt-3 font-mono text-[11px] leading-snug tracking-[0.02em] opacity-80 sm:text-[12px]">
                        {reveal
                          ? pickers.length
                            ? `Picked by ${pickers.join(", ")}`
                            : "Nobody picked"
                          : `${p.score} pts / ${p.bot ? "demo friend" : p.source === "spotify" ? "spotify" : "sample"}`}
                        {reveal && pts ? ` / +${pts}` : ""}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>

            {reveal ? (
              <p className="rise border-t border-line pt-4 font-mono text-[13px] leading-relaxed text-paper/90">
                <span className="text-mute">WHY &nbsp;/&nbsp; </span>
                {reveal.explain}
              </p>
            ) : (
              <p className="mt-auto font-mono text-[12px] tracking-[0.06em] text-mute">
                SELECTED &nbsp;/&nbsp;{" "}
                <span className="text-paper">
                  {selected ? byId[selected]?.name.toUpperCase() : "NOBODY YET"}
                </span>
              </p>
            )}
          </div>

          <aside className="flex flex-col gap-8 border-t border-line bg-app p-6 lg:border-l lg:border-t-0">
            <div>
              <Wordmark stacked className="text-[36px] text-paper" />
              <p className="mt-2 font-mono text-[11px] tracking-[0.06em] text-mute">
                Room {state.code} &nbsp;/&nbsp; Q{pad(q.index + 1)}
              </p>
            </div>

            <div>
              <p className="font-mono text-[11px] tracking-[0.08em] text-mute">
                WORKFLOW
              </p>
              <ol className="mt-4 flex flex-col gap-1 font-mono text-[13px]">
                {STEPS.map((s, i) => (
                  <li
                    key={s.id}
                    className={`rounded-[3px] border px-4 py-3 ${s.id === q.category ? "border-mute bg-tile text-paper" : "border-transparent text-paper/70"}`}
                  >
                    {pad(i + 1)} &nbsp; {s.label}
                  </li>
                ))}
              </ol>
            </div>

            <div>
              <p className="font-mono text-[11px] tracking-[0.08em] text-mute">
                CURRENT SESSION
              </p>
              <p className="mt-3 font-mono text-[13px] text-paper">
                Q {q.index + 1} OF {q.total} &nbsp;/&nbsp;{" "}
                {reveal ? "REVEALED" : `${q.time_left}S`}
              </p>
              <p className="mt-1 font-mono text-[12px] text-mute">
                {answered} of {total - 1} answered
              </p>
            </div>

            <Button
              variant="dark"
              onClick={cta.onClick}
              disabled={cta.disabled}
              className="mt-auto hidden lg:inline-flex min-h-14 w-full justify-start px-5"
            >
              {cta.label.toUpperCase()} <span aria-hidden>&rarr;</span>
            </Button>
          </aside>
        </div>
      </Slide>
      <div className="pointer-events-none fixed inset-x-3 bottom-3 z-30 lg:hidden">
        <Button onClick={cta.onClick} disabled={cta.disabled} className="pointer-events-auto min-h-14 w-full disabled:opacity-100 disabled:bg-tile disabled:text-paper/70">
          {cta.label} <span aria-hidden>&rarr;</span>
        </Button>
      </div>
    </Page>
  );
}

/* ---------------------------------------------------------------- report */

const STRAP = { red: "bg-red", mustard: "bg-mustard", green: "bg-green", blue: "bg-blue" } as const;
// Each badge hangs at its own height, like the deck's game-cards slide.
const DROP = ["h-40 sm:h-[260px]", "h-24 sm:h-[150px]", "h-44 sm:h-[280px]", "h-32 sm:h-[210px]"];
const DELAY = ["[animation-delay:0ms]", "[animation-delay:70ms]", "[animation-delay:140ms]", "[animation-delay:210ms]"];

function Report({ state, isHost, onRematch }: { state: RoomState; isHost: boolean; onRematch: () => void }) {
  const ranked = [...state.players].sort((a, b) => b.score - a.score);
  const host = state.players.find((p) => p.id === state.host_id);
  const cards = state.cards ?? [];

  return (
    <Page>
      <section className="relative -mt-3 overflow-hidden pb-4 sm:-mt-6 lg:-mt-8">
        <div className="grain absolute inset-x-0 top-[18%] h-[52%] rounded-[22px] bg-paper sm:rounded-[28px]" />
        <ul className="relative grid grid-cols-2 gap-x-5 px-3 sm:grid-cols-4 sm:gap-x-10 sm:px-[12%]">
          {cards.map((c, i) => (
            <li key={c.id} className={`swing flex flex-col items-center ${DELAY[i % 4]}`}>
              <div className={`grain w-7 sm:w-9 ${STRAP[c.color]} ${DROP[i % 4]}`} />
              <div className={`grain relative -mt-[16%] flex aspect-[3/4.2] w-full skew-y-[18deg] flex-col items-center justify-center px-3 ${STRAP[c.color]}`}>
                <span className="absolute left-[34%] top-[8%] h-[4.5%] w-[32%] rotate-[4deg] rounded-full bg-paper/80" />
                <div className="flex -skew-y-[18deg] flex-col items-center gap-2 pt-[18%] text-center text-paper">
                  <span className="font-display text-[clamp(11px,1.25vw,19px)] font-black uppercase leading-tight">{c.title}</span>
                  <span className="font-cond text-[clamp(30px,3.6vw,56px)] uppercase leading-none">{c.winner}</span>
                  <span className="caps text-[clamp(10px,0.9vw,13px)] leading-snug opacity-90">{c.stat}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
        <p className="display relative -mt-[0.25em] text-center text-[clamp(56px,10vw,170px)] text-paper">Game cards</p>
      </section>

      <section className="grain rounded-[22px] bg-ink px-6 py-14 ring-1 ring-cream/10 sm:rounded-[28px] sm:px-[8%] sm:py-20">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:items-center">
          <div className="relative">
            <Star className="absolute -left-6 -top-10 h-40 w-40 text-red sm:h-56 sm:w-56" />
            <h2 className="display relative text-[clamp(56px,6.2vw,112px)] text-paper">
              Final
              <br />
              scores
            </h2>
            <p className="caps relative mt-6 inline-block bg-blue px-6 py-4 text-[clamp(18px,2vw,30px)] leading-tight">Who knows the group best?</p>
          </div>
          <ol className="flex flex-col">
            {ranked.map((p, i) => (
              <li key={p.id} className="flex items-center gap-5 border-b-[3px] border-blue py-5 last:border-b-0">
                <Arrow flip className="h-8 w-14 shrink-0 text-leaf sm:h-10 sm:w-16" />
                <div className="min-w-0 flex-1">
                  <p className="font-cond text-[clamp(36px,4.4vw,64px)] uppercase leading-none text-paper">{p.name}</p>
                  <p className="mt-1 text-[clamp(15px,1.4vw,20px)] text-paper/80">
                    {i === 0 ? "Knows everyone's taste" : p.id === state.me ? "That's you" : `${pad(i + 1)} place`}
                  </p>
                </div>
                <p className="font-cond text-[clamp(32px,3.6vw,56px)] leading-none text-cream">{p.score}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <Slide tone="mustard" className="flex min-h-[60dvh] flex-col items-center justify-center gap-8 px-6 py-20 text-center">
        <p className="display text-[clamp(20px,2.6vw,40px)]">Connect. Guess. Reveal. Rematch.</p>
        {isHost ? (
          <Button tone="ink" onClick={onRematch} className="min-h-14 px-10 text-[17px]">
            Rematch
          </Button>
        ) : (
          <p className="caps text-[18px]">Waiting on {host?.name ?? "the host"} for the rematch.</p>
        )}
        <button onClick={() => go("/")} className="press caps text-[14px] underline underline-offset-4 hover:opacity-70 focus-visible:outline-2 focus-visible:outline-ink">
          New room
        </button>
      </Slide>
    </Page>
  );
}
