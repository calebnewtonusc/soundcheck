import {
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  ApiError,
  api,
  clearCreds,
  loadCreds,
  saveCreds,
  type Creds,
  type Mode,
  type RoomState,
} from "./api";
import { go } from "./App";
import { Game } from "./Game";
import { Report } from "./Report";
import { Join, SOURCE_LABEL } from "./Join";
import { savePass, type Profile, type Source } from "./profiles";
import { TasteBuilder } from "./Taste";
import {
  Avatar,
  Bubble,
  Button,
  Page,
  Slide,
  Star,
  Toast,
} from "./ui";

// One poll a second: fast enough that a reveal lands on every phone in the
// same beat, cheap enough for a room of twenty on one instance.
const POLL_MS = 1000;

export function Room({ code }: { code: string }) {
  const [creds, setCreds] = useState<Creds | null>(() => loadCreds(code));
  const [state, setState] = useState<RoomState | null>(null);
  const [missing, setMissing] = useState(false);
  const [offline, setOffline] = useState(false);
  const [error, setError] = useState("");
  const [blocked, setBlocked] = useState<string | null>(null);
  const [aiOn, setAiOn] = useState(false);

  useEffect(() => {
    api.health().then(
      (h) => setAiOn(h.ai),
      () => setAiOn(false),
    );
  }, []);

  // Coming back from Spotify: pick creds or an error off the URL, then clean it.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const pid = q.get("pid");
    const key = q.get("key");
    if (pid && key) {
      saveCreds(code, { pid, key });
      setCreds({ pid, key });
      // Back from Spotify: keep the profile on this phone for next time.
      api.myProfile(code, { pid, key }).then(
        (p) => savePass({ ...p, saved: Date.now() }),
        () => undefined,
      );
    }
    if (q.get("spotify") === "not_registered") setBlocked(q.get("name") ?? "");
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
      if (e instanceof ApiError && e.status === 404) setMissing(true);
      else setOffline(true);
    }
  }, [code, creds]);

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(t);
  }, [refresh]);

  // Every new screen (next question, reveal into report) starts at the top.
  const screen = state ? `${state.phase}:${state.question?.index ?? ""}` : "";
  useEffect(() => {
    if (screen) window.scrollTo({ top: 0 });
  }, [screen]);

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
            That code doesn't match an open room. Rooms close after two quiet
            hours.
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

  if (!state.me || !creds) {
    return (
      <>
        {toast}
        <Join
          code={code}
          state={state}
          onJoined={(c) => {
            saveCreds(code, c);
            setCreds(c);
          }}
          onError={setError}
          blocked={blocked}
        />
      </>
    );
  }

  const isHost = state.host_id === state.me;
  return (
    <>
      {toast}
      {state.phase === "lobby" && (
        <Lobby
          state={state}
          isHost={isHost}
          aiAvailable={aiOn}
          onBots={() => act(() => api.bots(code, creds))}
          onStart={() => act(() => api.start(code, creds))}
          onSettings={(s) => act(() => api.settings(code, creds, s))}
          onShuffle={() => act(() => api.shuffleTeams(code, creds))}
          onKick={(pid) => act(() => api.kick(code, creds, pid))}
          onTaste={(source, profile) => act(() => api.updateProfile(code, creds, source, profile))}
          onLeave={async () => {
            await act(() => api.leave(code, creds));
            clearCreds(code);
            go("/");
          }}
        />
      )}
      {(state.phase === "question" || state.phase === "reveal") && (
        <Game
          state={state}
          isHost={isHost}
          onAnswer={(id) => act(() => api.answer(code, creds, id))}
          onNext={() => act(() => api.next(code, creds))}
          onReact={(label) => act(() => api.react(code, creds, label))}
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

/* ----------------------------------------------------------------- lobby */

const LENGTHS = [
  { n: 5, label: "Quick" },
  { n: 8, label: "Classic" },
  { n: 12, label: "Long" },
];

const MODES: { id: Mode; label: string; line: string }[] = [
  { id: "classic", label: "Classic", line: "A bit of everything" },
  { id: "wrapped", label: "Wrapped", line: "Your whole year, called out" },
  {
    id: "roadtrip",
    label: "Road trip",
    line: "What's on repeat. 30s to answer",
  },
  { id: "decades", label: "Decades", line: "Release years and throwbacks" },
  { id: "genres", label: "Genres", line: "Who listens to what" },
];

function sourceLine(p: RoomState["players"][number]) {
  return p.bot ? "Demo friend" : SOURCE_LABEL[p.source];
}

type LobbyProps = {
  state: RoomState;
  isHost: boolean;
  aiAvailable: boolean;
  onBots: () => void;
  onStart: () => void;
  onSettings: (s: {
    length?: number;
    mode?: Mode;
    teams?: boolean;
    ai?: boolean;
  }) => void;
  onShuffle: () => void;
  onKick: (pid: string) => void;
  onTaste: (source: Source, profile: Profile) => Promise<void>;
  onLeave: () => void;
};

function Chip({
  on,
  onClick,
  children,
  className = "",
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={`press caps rounded-md border-2 px-3 py-2.5 text-left text-[14px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream ${
        on
          ? "border-cream bg-cream text-green"
          : "border-cream/50 hover:border-cream"
      } ${className}`}
    >
      {children}
    </button>
  );
}

function Lobby({
  state,
  isHost,
  aiAvailable,
  onBots,
  onStart,
  onSettings,
  onShuffle,
  onKick,
  onTaste,
  onLeave,
}: LobbyProps) {
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState<"picks" | "export" | null>(null);
  const me = state.players.find((p) => p.id === state.me);
  const [starting, setStarting] = useState(false);
  const host = state.players.find((p) => p.id === state.host_id);
  const link = `${window.location.origin}/room/${state.code}`;
  const allBots = state.players.filter((p) => p.bot).length >= 4;
  const mode = MODES.find((m) => m.id === state.mode) ?? MODES[0];

  async function invite() {
    try {
      if (navigator.share && window.matchMedia("(pointer: coarse)").matches) {
        await navigator.share({
          title: "SoundCheck",
          text: `Join my SoundCheck room ${state.code}`,
          url: link,
        });
        return;
      }
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  async function start() {
    setStarting(true);
    await onStart();
    setStarting(false);
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
            <Button variant="ghost" onClick={invite} className="self-start">
              {copied ? "Link copied" : "Invite friends"}
            </Button>

            {isHost ? (
              <>
                <fieldset>
                  <legend className="caps mb-3 text-[14px] opacity-80">
                    Mode
                  </legend>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2 xl:grid-cols-3">
                    {MODES.map((m) => (
                      <Chip
                        key={m.id}
                        on={state.mode === m.id}
                        onClick={() => onSettings({ mode: m.id })}
                      >
                        {m.label}
                        <span className="block font-mono text-[11px] normal-case leading-snug opacity-75">
                          {m.line}
                        </span>
                      </Chip>
                    ))}
                  </div>
                </fieldset>
                <fieldset>
                  <legend className="caps mb-3 text-[14px] opacity-80">
                    Length
                  </legend>
                  <div className="flex gap-2">
                    {LENGTHS.map((l) => (
                      <Chip
                        key={l.n}
                        on={state.length === l.n}
                        onClick={() => onSettings({ length: l.n })}
                        className="flex-1 text-center"
                      >
                        {l.label}
                        <span className="block font-mono text-[11px] normal-case opacity-75">
                          {l.n} questions
                        </span>
                      </Chip>
                    ))}
                  </div>
                </fieldset>
                <div className="flex flex-wrap gap-2">
                  <Chip
                    on={state.teams}
                    onClick={() => onSettings({ teams: !state.teams })}
                  >
                    Team mode {state.teams ? "on" : "off"}
                  </Chip>
                  {state.teams && (
                    <Chip on={false} onClick={onShuffle}>
                      Shuffle teams
                    </Chip>
                  )}
                  {aiAvailable && (
                    <Chip
                      on={state.ai}
                      onClick={() => onSettings({ ai: !state.ai })}
                    >
                      AI wording {state.ai ? "on" : "off"}
                    </Chip>
                  )}
                </div>
                {state.ai && (
                  <p className="font-mono text-[12px] leading-relaxed opacity-80">
                    Claude rewrites how each question sounds. Names, songs and
                    numbers stay exact, and the WHY under every answer is always
                    the plain fact.
                  </p>
                )}
                <p className="caps text-[clamp(15px,1.5vw,20px)] leading-snug opacity-90">
                  {state.players.length} in the room.{" "}
                  {state.players.length < 2
                    ? "Need at least 2 to play."
                    : "Enough to start."}
                </p>
                <div className="flex flex-col gap-3 sm:flex-row lg:flex-col xl:flex-row">
                  <Button
                    onClick={start}
                    disabled={state.players.length < 2 || starting}
                  >
                    {starting
                      ? state.ai
                        ? "Writing questions"
                        : "Starting"
                      : "Start the quiz"}
                  </Button>
                  {!allBots && (
                    <Button variant="ghost" onClick={onBots}>
                      Add demo friends
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <p className="caps text-[18px] leading-snug">
                {state.players.length} in the room. Waiting for{" "}
                {host?.name ?? "the host"} to start a {state.length}-question{" "}
                {mode.label} game
                {state.teams ? " in teams" : ""}.
              </p>
            )}
            {state.season && state.season.games > 0 && (
              <div className="rounded-md border-2 border-cream/40 p-4">
                <p className="caps text-[14px] opacity-80">
                  Season standings &middot; {state.season.games} {state.season.games === 1 ? "game" : "games"}
                </p>
                <ol className="mt-3 flex flex-col gap-1.5">
                  {state.season.table.slice(0, 6).map((r, i) => (
                    <li key={r.id} className={`flex items-baseline gap-3 ${r.here ? "" : "opacity-60"}`}>
                      <span className="font-mono text-[12px] opacity-70">{String(i + 1).padStart(2, "0")}</span>
                      <span className="font-cond flex-1 truncate text-[24px] uppercase leading-none">{r.name}</span>
                      <span className="font-mono text-[12px]">
                        {r.wins} {r.wins === 1 ? "win" : "wins"} / {r.points} pts
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {me && (
              <div className="flex flex-col gap-2">
                <p className="font-mono text-[12px] opacity-80">
                  You're in as {me.name} with {SOURCE_LABEL[me.source]}.
                </p>
                <div className="flex flex-wrap gap-x-5 gap-y-2">
                  <button type="button" onClick={() => setEditing("picks")} className="press caps text-[13px] underline underline-offset-4 opacity-85 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream">
                    Update my picks
                  </button>
                  <button type="button" onClick={() => setEditing("export")} className="press caps text-[13px] underline underline-offset-4 opacity-85 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream">
                    Upload Spotify data
                  </button>
                  <button
                    onClick={onLeave}
                    className="press caps text-[13px] underline underline-offset-4 opacity-75 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
                  >
                    Leave room and delete my data
                  </button>
                </div>
              </div>
            )}
            {editing && (
              <div role="dialog" aria-label="Update your taste" className="fixed inset-0 z-40 flex items-end justify-center bg-ink/70 p-3 sm:items-center">
                <div className="grain max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-[22px] bg-red p-6 text-cream">
                  <p className="display mb-5 text-[32px]">Update your taste</p>
                  <TasteBuilder
                    kind={editing}
                    onCancel={() => setEditing(null)}
                    onDone={async (r) => {
                      await onTaste(r.source, r.profile);
                      if (me) savePass({ name: me.name, avatar: me.avatar, source: r.source, profile: r.profile, saved: Date.now(), through: r.through });
                      setEditing(null);
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <ul className="flex flex-col gap-14 pb-6" aria-label="Players">
            {state.players.map((p, i) => (
              <li key={p.id} className="rise flex flex-col">
                <Bubble side={i % 2 ? "right" : "left"} filled={i % 2 === 1}>
                  <span className="flex items-center gap-4">
                    <Avatar
                      name={p.name}
                      src={p.avatar}
                      index={i}
                      className="h-11 w-11 text-[22px] ring-2 ring-cream"
                    />
                    <span>
                      &ldquo;{p.name} is in.&rdquo;
                      <span className="mt-1 block font-mono text-[12px] normal-case tracking-[0.04em] opacity-75">
                        {sourceLine(p)}
                        {p.id === state.host_id ? " / host" : ""}
                        {p.id === state.me ? " / you" : ""}
                      </span>
                    </span>
                    {state.teams && p.team && (
                      <span
                        className={`caps rounded-full px-3 py-1 text-[12px] ${p.team === "red" ? "bg-red" : "bg-blue"}`}
                      >
                        Team {p.team}
                      </span>
                    )}
                    {isHost && p.id !== state.me && (
                      <button
                        onClick={() => onKick(p.id)}
                        aria-label={`Remove ${p.name}`}
                        className="press ml-1 rounded-full px-2 font-mono text-[18px] leading-none opacity-60 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
                      >
                        &times;
                      </button>
                    )}
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
