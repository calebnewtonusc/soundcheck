import type { ButtonHTMLAttributes, ReactNode } from "react";

/** The deck's 12-spike starburst. */
export function Star({ className = "" }: { className?: string }) {
  const pts: string[] = [];
  for (let i = 0; i < 24; i++) {
    const r = i % 2 === 0 ? 50 : 20;
    const a = (Math.PI * 2 * i) / 24 - Math.PI / 2;
    pts.push(
      `${(50 + r * Math.cos(a)).toFixed(1)},${(50 + r * Math.sin(a)).toFixed(1)}`,
    );
  }
  return (
    <svg viewBox="0 0 100 100" aria-hidden className={className}>
      <polygon points={pts.join(" ")} fill="currentColor" />
    </svg>
  );
}

/** The wordmark, with the starburst standing in for the O, oversized like the cover. */
export function Wordmark({
  stacked = false,
  className = "",
}: {
  stacked?: boolean;
  className?: string;
}) {
  const o = (
    <Star className="inline-block h-[1.45em] w-[1.45em] -my-[0.25em] -mx-[0.12em] align-middle" />
  );
  return (
    <h1 className={`display select-none ${className}`} aria-label="SoundCheck">
      {stacked ? (
        <>
          <span className="block">S{o}UND</span>
          <span className="block">CHECK</span>
        </>
      ) : (
        <span className="whitespace-nowrap">S{o}UNDCHECK</span>
      )}
    </h1>
  );
}

const PANELS = {
  blue: "bg-blue text-cream",
  cream: "bg-cream text-blue",
  green: "bg-green text-cream",
  red: "bg-red text-cream",
  mustard: "bg-mustard text-ink",
  ink: "bg-ink text-cream",
} as const;
export type Tone = keyof typeof PANELS;

/** A slide: a rounded, grainy color card sitting on the dark frame. */
export function Slide({
  tone,
  children,
  className = "",
  corner = true,
}: {
  tone: Tone;
  children: ReactNode;
  className?: string;
  corner?: boolean;
}) {
  const starTone =
    tone === "mustard"
      ? "text-ink"
      : tone === "cream"
        ? "text-red"
        : "text-cream";
  return (
    <section
      className={`grain rounded-[22px] sm:rounded-[28px] ${PANELS[tone]} ${className}`}
    >
      {children}
      {corner && (
        <Star
          className={`pointer-events-none absolute bottom-4 left-4 h-10 w-10 sm:bottom-6 sm:left-6 sm:h-16 sm:w-16 ${starTone}`}
        />
      )}
    </section>
  );
}

export function Page({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[1500px] flex-col gap-4 p-3 sm:gap-6 sm:p-6 lg:p-8">
      {children}
    </main>
  );
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "solid" | "ghost" | "dark";
  tone?: "cream" | "ink";
};

export function Button({
  variant = "solid",
  tone = "cream",
  className = "",
  ...rest
}: BtnProps) {
  const base =
    "press caps inline-flex min-h-12 items-center justify-center gap-3 rounded-full px-7 text-[15px] tracking-wide disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-2 focus-visible:outline-offset-4";
  const styles =
    variant === "solid"
      ? tone === "cream"
        ? "bg-cream text-ink hover:bg-paper focus-visible:outline-cream"
        : "bg-ink text-cream hover:bg-black focus-visible:outline-ink"
      : variant === "ghost"
        ? tone === "cream"
          ? "border-2 border-cream/80 text-cream hover:bg-cream/10 focus-visible:outline-cream"
          : "border-2 border-ink text-ink hover:bg-ink/10 focus-visible:outline-ink"
        : "rounded-none border border-cream/70 font-mono text-[13px] normal-case tracking-[0.06em] text-cream hover:bg-cream hover:text-app focus-visible:outline-cream";
  return <button className={`${base} ${styles} ${className}`} {...rest} />;
}

/** The thick rounded green arrow from the "make it social" slide. */
export function Arrow({
  className = "",
  flip = false,
}: {
  className?: string;
  flip?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 220 60"
      aria-hidden
      className={`${flip ? "-scale-x-100" : ""} ${className}`}
    >
      <path
        d="M200 30H28M58 6 28 30l30 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="18"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Outline speech bubble with a tail, from the "taste to the test" slide. */
export function Bubble({
  children,
  side = "left",
  filled = false,
  className = "",
}: {
  children: ReactNode;
  side?: "left" | "right";
  filled?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`relative ${side === "right" ? "self-end" : "self-start"} ${className}`}
    >
      <div
        className={`caps rounded-[34px] border-[5px] border-cream px-6 py-4 text-[clamp(15px,2.1vw,26px)] leading-tight sm:px-9 sm:py-5 ${filled ? "bg-bubble" : "bg-green"}`}
      >
        {children}
      </div>
      <svg
        viewBox="0 0 60 50"
        aria-hidden
        className={`absolute -bottom-[34px] h-10 w-12 text-cream ${filled ? "fill-bubble" : "fill-green"} ${side === "right" ? "right-10 -scale-x-100" : "left-10"}`}
      >
        <path
          d="M6 0v44L44 4"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

export function Toast({
  message,
  onClose,
}: {
  message: string;
  onClose: () => void;
}) {
  return (
    <div
      role="alert"
      className="caps fixed inset-x-3 top-3 z-50 mx-auto flex max-w-xl items-center justify-between gap-4 rounded-md bg-red px-5 py-4 text-[14px] text-cream ring-1 ring-cream/30"
    >
      <span>{message}</span>
      <button
        onClick={onClose}
        className="press font-mono text-[12px] normal-case underline underline-offset-4 hover:text-paper"
      >
        close
      </button>
    </div>
  );
}

/** A player's face: their Spotify photo, or their initial on a deck color. */
const AVATAR_TONES = ["bg-red", "bg-mustard", "bg-green", "bg-blue"];
export function Avatar({ name, src, index = 0, className = "" }: { name: string; src: string | null; index?: number; className?: string }) {
  if (src) return <img src={src} alt="" className={`shrink-0 rounded-full object-cover ${className}`} />;
  return (
    <span aria-hidden className={`grain inline-flex shrink-0 items-center justify-center rounded-full font-cond leading-none text-paper ${AVATAR_TONES[index % 4]} ${className}`}>
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

/** Album or artist art in the deck's cream photo mat. */
export function Art({ src, alt, className = "", round = false }: { src: string | null; alt: string; className?: string; round?: boolean }) {
  return (
    <div className={`shrink-0 overflow-hidden bg-tile ${round ? "rounded-full" : "rounded-[3px]"} ${className}`}>
      {src ? <img src={src} alt={alt} className="h-full w-full object-cover" /> : <Star className="m-[22%] h-[56%] w-[56%] text-line" />}
    </div>
  );
}
