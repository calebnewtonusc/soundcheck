import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import type { Card, RoomState } from "./api";
import { go } from "./App";
import { Arrow, Button, Page, Slide, Star, Wordmark } from "./ui";

const pad = (n: number) => String(n).padStart(2, "0");
const STRAP = {
  red: "bg-red",
  mustard: "bg-mustard",
  green: "bg-green",
  blue: "bg-blue",
} as const;
// Each badge hangs at its own height, like the deck's game-cards slide.
const DROP = [
  "h-40 sm:h-[260px]",
  "h-24 sm:h-[150px]",
  "h-44 sm:h-[280px]",
  "h-32 sm:h-[210px]",
];
const DELAY = [
  "[animation-delay:0ms]",
  "[animation-delay:70ms]",
  "[animation-delay:140ms]",
  "[animation-delay:210ms]",
];

type Props = { state: RoomState; isHost: boolean; onRematch: () => void };

export function Report({ state, isHost, onRematch }: Props) {
  const ranked = [...state.players].sort((a, b) => b.score - a.score);
  // Only a clear, nonzero leader "knows everyone's taste"; a 0-0 tie doesn't.
  const clearWinner = ranked.length > 0 && ranked[0].score > 0 && (ranked.length === 1 || ranked[0].score > ranked[1].score);
  const host = state.players.find((p) => p.id === state.host_id);
  const cards = state.cards ?? [];
  const meIndex = ranked.findIndex((p) => p.id === state.me);
  const me = ranked[meIndex];
  const myCard = cards.find((c) => c.pid === state.me) ?? null;

  return (
    <Page>
      <section className="relative -mt-3 overflow-hidden pb-4 sm:-mt-6 lg:-mt-8">
        <div className="grain absolute inset-x-0 top-[18%] h-[52%] rounded-[22px] bg-paper sm:rounded-[28px]" />
        <ul className="relative grid grid-cols-2 gap-x-5 px-3 sm:grid-cols-4 sm:gap-x-10 sm:px-[12%]">
          {cards.map((c, i) => (
            <li
              key={c.id}
              className={`swing flex flex-col items-center ${DELAY[i % 4]}`}
            >
              <div
                className={`grain w-7 sm:w-9 ${STRAP[c.color]} ${DROP[i % 4]}`}
              />
              <Badge card={c} />
            </li>
          ))}
        </ul>
        <p className="display relative -mt-[0.25em] text-center text-[clamp(56px,10vw,170px)] text-paper">
          Game cards
        </p>
      </section>

      {state.team_scores && <TeamBanner scores={state.team_scores} />}

      <section className="grain rounded-[22px] bg-ink px-6 py-14 ring-1 ring-cream/10 sm:rounded-[28px] sm:px-[8%] sm:py-20">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:items-center">
          <div className="relative">
            <Star className="absolute -left-6 -top-10 h-40 w-40 text-red sm:h-56 sm:w-56" />
            <h2 className="display relative text-[clamp(56px,6.2vw,112px)] text-paper">
              Final
              <br />
              scores
            </h2>
            <p className="caps relative mt-6 inline-block bg-blue px-6 py-4 text-[clamp(18px,2vw,30px)] leading-tight">
              Who knows the group best?
            </p>
          </div>
          <ol className="flex flex-col">
            {ranked.map((p, i) => (
              <li
                key={p.id}
                className="flex items-center gap-5 border-b-[3px] border-blue py-5 last:border-b-0"
              >
                <Arrow
                  flip
                  className="h-8 w-14 shrink-0 text-leaf sm:h-10 sm:w-16"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-cond text-[clamp(36px,4.4vw,64px)] uppercase leading-none text-paper">
                    {p.name}
                  </p>
                  <p className="mt-1 text-[clamp(15px,1.4vw,20px)] text-paper/80">
                    {i === 0 && clearWinner ? "Knows everyone's taste" : `${pad(i + 1)} place`}{" "}
                    &middot; {p.right} right
                    {p.id === state.me ? " · you" : ""}
                  </p>
                </div>
                <p className="font-cond text-[clamp(32px,3.6vw,56px)] leading-none text-cream">
                  {p.score}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {me && (
        <ShareSlide
          name={me.name}
          place={meIndex + 1}
          of={ranked.length}
          score={me.score}
          right={me.right}
          card={myCard}
          code={state.code}
        />
      )}

      <Slide
        tone="mustard"
        className="flex min-h-[54dvh] flex-col items-center justify-center gap-8 px-6 py-20 text-center"
      >
        <p className="display text-[clamp(20px,2.6vw,40px)]">
          Connect. Guess. Reveal. Rematch.
        </p>
        {isHost ? (
          <Button
            tone="ink"
            onClick={onRematch}
            className="min-h-14 px-10 text-[17px]"
          >
            Rematch
          </Button>
        ) : (
          <p className="caps text-[18px]">
            Waiting on {host?.name ?? "the host"} for the rematch.
          </p>
        )}
        <button
          onClick={() => go("/")}
          className="press caps text-[14px] underline underline-offset-4 hover:opacity-70 focus-visible:outline-2 focus-visible:outline-ink"
        >
          New room
        </button>
      </Slide>
    </Page>
  );
}

function Badge({ card, big = false }: { card: Card; big?: boolean }) {
  return (
    <div
      className={`grain relative -mt-[16%] flex aspect-[3/4.2] w-full skew-y-[18deg] flex-col items-center justify-center px-3 ${STRAP[card.color]}`}
    >
      <span className="absolute left-[34%] top-[8%] h-[4.5%] w-[32%] rotate-[4deg] rounded-full bg-paper/80" />
      <div className="flex -skew-y-[18deg] flex-col items-center gap-2 pt-[18%] text-center text-paper">
        <span
          className={`font-display font-black uppercase leading-tight ${big ? "text-[44px]" : "text-[clamp(11px,1.25vw,19px)]"}`}
        >
          {card.title}
        </span>
        <span
          className={`font-cond uppercase leading-none ${big ? "text-[150px]" : "text-[clamp(30px,3.6vw,56px)]"}`}
        >
          {card.winner}
        </span>
        <span
          className={`caps leading-snug opacity-90 ${big ? "max-w-[80%] text-[30px]" : "text-[clamp(10px,0.9vw,13px)]"}`}
        >
          {card.stat}
        </span>
      </div>
    </div>
  );
}

/** The story-sized card people post. Rendered off screen, saved as a PNG. */
function ShareSlide({
  name,
  place,
  of,
  score,
  right,
  card,
  code,
}: {
  name: string;
  place: number;
  of: number;
  score: number;
  right: number;
  card: Card | null;
  code: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"idle" | "busy" | "done" | "error">(
    "idle",
  );

  async function save() {
    if (!ref.current) return;
    setStatus("busy");
    try {
      const url = await toPng(ref.current, { pixelRatio: 1, cacheBust: true });
      const blob = await (await fetch(url)).blob();
      const file = new File([blob], `soundcheck-${name.toLowerCase()}.png`, {
        type: "image/png",
      });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: "My SoundCheck" });
      } else {
        const a = document.createElement("a");
        a.href = url;
        a.download = file.name;
        a.click();
      }
      setStatus("done");
    } catch (e) {
      // A cancelled share sheet is not an error.
      setStatus(
        e instanceof DOMException && e.name === "AbortError" ? "idle" : "error",
      );
    }
  }

  return (
    <Slide
      tone="blue"
      className="flex flex-col items-center gap-8 px-6 py-16 text-center sm:py-20"
    >
      <p className="display text-[clamp(30px,4.6vw,72px)]">
        Take it to the group chat
      </p>
      <div className="h-[480px] w-[270px] overflow-hidden rounded-2xl ring-4 ring-cream">
        {/* 270 / 1080 = 0.25: the real 1080x1920 card, shown at a quarter. */}
        <div className="origin-top-left scale-[0.25]">
          <StoryCard
            name={name}
            place={place}
            of={of}
            score={score}
            right={right}
            card={card}
            code={code}
          />
        </div>
      </div>
      <Button onClick={save} disabled={status === "busy"}>
        {status === "busy"
          ? "Making your card"
          : status === "done"
            ? "Saved. Post it"
            : "Save my card"}
      </Button>
      {status === "error" && (
        <p className="caps text-[14px]">
          Couldn't make the image on this browser. Screenshot works too.
        </p>
      )}
      <div
        className="pointer-events-none fixed -left-[5000px] top-0"
        aria-hidden
      >
        <div ref={ref}>
          <StoryCard
            name={name}
            place={place}
            of={of}
            score={score}
            right={right}
            card={card}
            code={code}
          />
        </div>
      </div>
    </Slide>
  );
}

function StoryCard({
  name,
  place,
  of,
  score,
  right,
  card,
  code,
}: {
  name: string;
  place: number;
  of: number;
  score: number;
  right: number;
  card: Card | null;
  code: string;
}) {
  return (
    <div className="grain flex h-[1920px] w-[1080px] flex-col items-center justify-between bg-blue px-[90px] py-[140px] text-cream">
      <Wordmark stacked className="text-center text-[170px]" />
      {card ? (
        <div className="flex w-[640px] flex-col items-center">
          <div className={`grain h-[220px] w-[64px] ${STRAP[card.color]}`} />
          <Badge card={card} big />
        </div>
      ) : (
        <div className="flex flex-col items-center gap-6">
          <Star className="h-[260px] w-[260px] text-cream" />
          <p className="font-cond text-[150px] uppercase leading-none">
            {name}
          </p>
        </div>
      )}
      <div className="flex flex-col items-center gap-6">
        <p className="caps text-[56px] leading-tight">
          {place === 1 && score > 0
            ? "Knew everyone's taste"
            : `${pad(place)} of ${pad(of)}`}
        </p>
        <p className="font-cond text-[120px] leading-none">{score} pts</p>
        <p className="caps text-[38px] opacity-85">
          {right} right &middot; Room {code}
        </p>
        <p className="mt-6 font-mono text-[32px] opacity-75">
          playsoundcheck.up.railway.app
        </p>
      </div>
    </div>
  );
}

function TeamBanner({ scores }: { scores: { red: number; blue: number } }) {
  const tie = scores.red === scores.blue;
  const winner = scores.red > scores.blue ? "red" : "blue";
  return (
    <section
      className={`grain flex flex-col items-center gap-4 rounded-[22px] px-6 py-14 text-center text-cream sm:rounded-[28px] ${tie ? "bg-mustard text-ink" : winner === "red" ? "bg-red" : "bg-blue"}`}
    >
      <p className="caps text-[clamp(15px,1.6vw,22px)] opacity-90">Team mode</p>
      <p className="display text-[clamp(44px,8vw,140px)]">
        {tie ? "Dead even" : `Team ${winner} wins`}
      </p>
      <p className="font-cond text-[clamp(28px,3.4vw,52px)] uppercase">
        Red {scores.red} &nbsp;/&nbsp; Blue {scores.blue}
      </p>
    </section>
  );
}
