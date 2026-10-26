import { useEffect, useState } from "react";
import { REACTIONS, type Option, type Player, type RoomState } from "./api";
import { Art, Avatar, Button, Page, Slide, Star, Wordmark } from "./ui";

const pad = (n: number) => String(n).padStart(2, "0");

const STEPS = [
  { id: "songs", label: "Top songs" },
  { id: "artists", label: "Top artists" },
  { id: "genre", label: "Genre + habits" },
  { id: "report", label: "Report" },
];

type Props = {
  state: RoomState;
  isHost: boolean;
  onAnswer: (id: string) => void;
  onNext: () => void;
  onReact: (label: string) => void;
};

export function Game({ state, isHost, onAnswer, onNext, onReact }: Props) {
  const q = state.question;
  const [picked, setPicked] = useState<string | null>(null);
  const index = q?.index;
  useEffect(() => setPicked(null), [index]);
  if (!q) return null;

  const reveal = state.phase === "reveal" ? state.reveal : undefined;
  const locked = q.my_answer;
  const selected = locked ?? picked;
  const byId = Object.fromEntries(state.players.map((p) => [p.id, p]));
  const last = q.index + 1 === q.total;
  const canPick = !reveal && !locked && !q.about_me;

  function lockIn() {
    if (!picked) return;
    navigator.vibrate?.(18);
    onAnswer(picked);
  }

  let cta: { label: string; onClick?: () => void; disabled?: boolean };
  if (reveal) {
    cta = isHost
      ? { label: last ? "See the report" : "Next question", onClick: onNext }
      : { label: "Host moves on", disabled: true };
  } else if (!canPick) {
    cta = isHost
      ? { label: "Reveal now", onClick: onNext }
      : {
          label: q.about_me
            ? "It's about you"
            : `Locked in, waiting on ${q.waiting_on}`,
          disabled: true,
        };
  } else {
    cta = { label: "Lock it in", onClick: lockIn, disabled: !picked };
  }

  const pickersOf = (id: string) =>
    reveal
      ? Object.entries(reveal.picks)
          .filter(([, c]) => c === id)
          .map(([pid]) => byId[pid])
          .filter(Boolean)
      : [];
  const optionTone = (id: string) => {
    if (reveal)
      return reveal.correct.includes(id)
        ? "border-cream bg-cream text-app"
        : "border-line bg-tile text-paper/45";
    if (selected === id) return "border-paper bg-tile-up text-paper";
    return "border-line bg-tile text-paper hover:border-mute";
  };
  const optionClass = (id: string) =>
    `press flex h-full w-full rounded-[3px] border text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream disabled:cursor-default ${optionTone(id)}`;

  return (
    <Page>
      <Slide
        tone="blue"
        className="flex min-h-[calc(100dvh-24px)] items-center justify-center p-3 pb-32 sm:min-h-[calc(100dvh-48px)] sm:p-[3.5%] lg:px-[6%] lg:pb-[3.5%]"
      >
        <div className="grid w-full overflow-hidden rounded-[22px] bg-app text-paper lg:grid-cols-[minmax(0,1fr)_290px]">
          <div className="halftone flex flex-col gap-6 p-5 sm:gap-7 sm:p-9">
            <div className="flex items-center gap-4 font-mono text-[11px] tracking-[0.08em] text-mute">
              <span>
                {pad(q.index + 1)} / {pad(q.total)}
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
                {q.image && (
                  <Art
                    src={q.image}
                    alt=""
                    className="mb-4 h-20 w-20 border-4 border-cream sm:hidden"
                  />
                )}
                <h2 className="font-ui text-[clamp(28px,3.9vw,58px)] font-medium leading-[1.03] tracking-[-0.02em]">
                  {q.text}
                </h2>
              </div>
            </div>

            {q.about_me && !reveal && (
              <p className="caps flex items-center gap-3 rounded-md bg-mustard px-4 py-3 text-[14px] text-ink">
                <Star className="h-5 w-5 shrink-0" /> This one's about you. Keep
                a straight face.
              </p>
            )}

            {q.kind === "who" ? (
              <ul
                className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3"
                aria-label="Who is it?"
              >
                {state.players.map((p, i) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      disabled={!canPick}
                      onClick={() => setPicked(p.id)}
                      aria-pressed={selected === p.id}
                      className={`${optionClass(p.id)} min-h-[128px] flex-col justify-between p-4 sm:min-h-[150px] sm:p-5`}
                    >
                      <span className="flex items-center justify-between font-mono text-[11px] tracking-[0.06em]">
                        {pad(i + 1)} / {pad(state.players.length)}
                        {reveal?.correct.includes(p.id) ? (
                          <Star className="h-5 w-5 text-red" />
                        ) : !reveal && p.answered ? (
                          <span className="opacity-70">IN</span>
                        ) : null}
                      </span>
                      <span className="mt-3 flex items-center gap-3">
                        <Avatar
                          name={p.name}
                          src={p.avatar}
                          index={i}
                          className="h-8 w-8 text-[17px]"
                        />
                        <span className="truncate font-ui text-[clamp(17px,1.7vw,23px)] font-medium uppercase">
                          {p.name}
                        </span>
                      </span>
                      <Footer
                        reveal={!!reveal}
                        pickers={pickersOf(p.id)}
                        idle={`${p.score} pts${p.streak > 1 ? ` / x${p.streak} streak` : ""}`}
                      />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <ul
                className="grid gap-3 sm:grid-cols-2 sm:gap-4"
                aria-label="Pick one"
              >
                {q.options.map((o) => (
                  <li key={o.id}>
                    <OptionCard
                      o={o}
                      disabled={!canPick}
                      selected={selected === o.id}
                      className={optionClass(o.id)}
                      onPick={() => setPicked(o.id)}
                      right={!!reveal?.correct.includes(o.id)}
                    >
                      <Footer
                        reveal={!!reveal}
                        pickers={pickersOf(o.id)}
                        idle=""
                      />
                    </OptionCard>
                  </li>
                ))}
              </ul>
            )}

            {reveal ? (
              <div className="rise flex flex-col gap-4 border-t border-line pt-4">
                <p className="font-mono text-[13px] leading-relaxed text-paper/90">
                  <span className="text-mute">WHY &nbsp;/&nbsp; </span>
                  {reveal.explain}
                </p>
                <div className="flex flex-wrap items-center gap-2" aria-label="React">
                  <span className="mr-1 font-mono text-[11px] tracking-[0.08em] text-mute">DEBATE IT</span>
                  {REACTIONS.map((label) => {
                    const who = reveal.reactions.filter(([, l]) => l === label).map(([pid]) => byId[pid]?.name).filter(Boolean);
                    const mine = reveal.reactions.some(([pid, l]) => pid === state.me && l === label);
                    return (
                      <button
                        key={label}
                        type="button"
                        onClick={() => onReact(label)}
                        aria-pressed={mine}
                        title={who.join(", ")}
                        className={`press rounded-full border px-3.5 py-1.5 font-mono text-[12px] tracking-[0.04em] focus-visible:outline-2 focus-visible:outline-cream ${
                          mine ? "border-cream bg-cream text-app" : "border-line text-paper/80 hover:border-mute"
                        }`}
                      >
                        {label}
                        {who.length ? ` ${who.length}` : ""}
                      </button>
                    );
                  })}
                </div>
                {reveal.reactions.length > 0 && (
                  <p className="font-mono text-[11px] leading-relaxed text-mute">
                    {reveal.reactions
                      .slice(-4)
                      .map(([pid, l]) => `${byId[pid]?.name ?? "Someone"}: ${l}`)
                      .join("  /  ")}
                  </p>
                )}
              </div>
            ) : (
              <p className="mt-auto font-mono text-[12px] tracking-[0.06em] text-mute">
                SELECTED &nbsp;/&nbsp;{" "}
                <span className="text-paper">
                  {selectedLabel(q, selected, byId)}
                </span>
              </p>
            )}
          </div>

          <Sidebar state={state} category={q.category} cta={cta} />
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

function selectedLabel(
  q: NonNullable<RoomState["question"]>,
  id: string | null,
  byId: Record<string, Player>,
) {
  if (!id) return "NOBODY YET";
  const label =
    q.kind === "who"
      ? byId[id]?.name
      : q.options.find((o) => o.id === id)?.label;
  return (label ?? "").toUpperCase();
}

function OptionCard({
  o,
  disabled,
  selected,
  className,
  onPick,
  right,
  children,
}: {
  o: Option;
  disabled: boolean;
  selected: boolean;
  className: string;
  onPick: () => void;
  right: boolean;
  children: React.ReactNode;
}) {
  const isGenre = !o.image && !o.sub;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onPick}
      aria-pressed={selected}
      className={`${className} min-h-[96px] items-center gap-4 p-3 sm:p-4`}
    >
      {!isGenre && (
        <Art
          src={o.image}
          alt=""
          className="h-[68px] w-[68px] sm:h-20 sm:w-20"
          round={!o.sub}
        />
      )}
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span
          className={`font-ui font-medium leading-tight ${isGenre ? "text-[clamp(20px,2vw,28px)] uppercase" : "text-[clamp(16px,1.5vw,20px)]"}`}
        >
          {o.label}
        </span>
        {o.sub && (
          <span className="truncate font-mono text-[12px] opacity-75">
            {o.sub}
          </span>
        )}
        {children}
      </span>
      {right && <Star className="h-6 w-6 shrink-0 self-start text-red" />}
    </button>
  );
}

function Footer({
  reveal,
  pickers,
  points,
  idle,
}: {
  reveal: boolean;
  pickers: Player[];
  points?: number;
  idle: string;
}) {
  if (!reveal)
    return idle ? (
      <span className="mt-3 font-mono text-[11px] tracking-[0.02em] opacity-75 sm:text-[12px]">
        {idle}
      </span>
    ) : null;
  return (
    <span className="mt-2 font-mono text-[11px] leading-snug tracking-[0.02em] opacity-85 sm:text-[12px]">
      {pickers.length
        ? `Picked by ${pickers.map((p) => p.name).join(", ")}`
        : "Nobody picked"}
      {points ? ` / +${points}` : ""}
    </span>
  );
}

function Sidebar({
  state,
  category,
  cta,
}: {
  state: RoomState;
  category: string;
  cta: { label: string; onClick?: () => void; disabled?: boolean };
}) {
  const q = state.question!;
  const board = [...state.players]
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
  return (
    <aside className="flex flex-col gap-7 border-t border-line bg-app p-6 lg:border-l lg:border-t-0">
      <div>
        <Wordmark stacked className="text-[34px] text-paper" />
        <p className="mt-2 font-mono text-[11px] tracking-[0.06em] text-mute">
          Room {state.code} &nbsp;/&nbsp; Q{pad(q.index + 1)}
        </p>
      </div>

      <div className="hidden lg:block">
        <p className="font-mono text-[11px] tracking-[0.08em] text-mute">
          WORKFLOW
        </p>
        <ol className="mt-3 flex flex-col gap-1 font-mono text-[13px]">
          {STEPS.map((s, i) => (
            <li
              key={s.id}
              className={`rounded-[3px] border px-4 py-2.5 ${s.id === category ? "border-mute bg-tile text-paper" : "border-transparent text-paper/65"}`}
            >
              {pad(i + 1)} &nbsp; {s.label}
            </li>
          ))}
        </ol>
      </div>

      {state.team_scores && (
        <div className="grid grid-cols-2 gap-2 font-mono text-[12px]">
          {(["red", "blue"] as const).map((t) => (
            <div key={t} className={`rounded-[3px] px-3 py-2.5 text-paper ${t === "red" ? "bg-red" : "bg-blue"}`}>
              <span className="block text-[11px] tracking-[0.08em] opacity-80">TEAM {t.toUpperCase()}</span>
              <span className="text-[18px] tabular-nums">{state.team_scores![t]}</span>
            </div>
          ))}
        </div>
      )}

      <div>
        <p className="font-mono text-[11px] tracking-[0.08em] text-mute">
          LEADERBOARD
        </p>
        <ol className="mt-3 flex flex-col gap-2 font-mono text-[13px]">
          {board.map((p, i) => (
            <li
              key={p.id}
              className={`flex items-center gap-3 ${p.id === state.me ? "text-paper" : "text-paper/70"}`}
            >
              <span className="w-5 text-mute">{pad(i + 1)}</span>
              <span className="flex-1 truncate uppercase">{p.name}</span>
              {state.reveal?.points[p.id] ? (
                <span className="text-gain">
                  +{state.reveal.points[p.id]}
                </span>
              ) : p.streak > 1 ? (
                <span className="text-mustard">x{p.streak}</span>
              ) : null}
              <span className="tabular-nums">{p.score}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-auto hidden lg:block">
        <Button
        variant="dark"
        onClick={cta.onClick}
        disabled={cta.disabled}
        className="min-h-14 w-full justify-start px-5"
      >
        {cta.label.toUpperCase()} <span aria-hidden>&rarr;</span>
      </Button>
      </div>
    </aside>
  );
}
