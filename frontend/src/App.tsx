import { useEffect, useState, type FormEvent } from "react";
import { api } from "./api";
import { Room } from "./Room";
import { Arrow, Button, Page, Slide, Star, Toast, Wordmark } from "./ui";

function useRoute() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const on = () => setPath(window.location.pathname);
    window.addEventListener("popstate", on);
    return () => window.removeEventListener("popstate", on);
  }, []);
  return path;
}

export function go(path: string) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export default function App() {
  const path = useRoute();
  const match = path.match(/^\/room\/([A-Za-z]{4})\/?$/);
  if (match) return <Room code={match[1].toUpperCase()} />;
  return <Home />;
}

function SpotifyLockup() {
  return (
    <div className="flex items-center justify-center gap-3 text-[clamp(26px,3.6vw,52px)] font-bold tracking-tight">
      <svg viewBox="0 0 100 100" aria-hidden className="h-[1.5em] w-[1.5em]">
        <circle cx="50" cy="50" r="50" fill="currentColor" />
        <g fill="none" className="stroke-blue" strokeLinecap="round">
          <path d="M24 38c18-6 38-5 54 4" strokeWidth="8" />
          <path d="M27 54c15-4 31-3 44 4" strokeWidth="7" />
          <path d="M30 68c12-3 24-2 34 3" strokeWidth="6" />
        </g>
      </svg>
      <span className="font-body">Spotify</span>
    </div>
  );
}

function Home() {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(
    new URLSearchParams(window.location.search).get("error") ?? "",
  );

  async function create() {
    setBusy(true);
    try {
      const { code } = await api.create();
      go(`/room/${code}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't make a room.");
      setBusy(false);
    }
  }

  function join(e: FormEvent) {
    e.preventDefault();
    const c = code.trim().toUpperCase();
    if (/^[A-Z]{4}$/.test(c)) go(`/room/${c}`);
    else setError("Room codes are 4 letters.");
  }

  return (
    <Page>
      {error && <Toast message={error} onClose={() => setError("")} />}

      <Slide
        tone="blue"
        className="flex min-h-[calc(100dvh-24px)] flex-col items-center justify-center px-5 py-20 text-center sm:min-h-[calc(100dvh-48px)] lg:min-h-[calc(100dvh-64px)]"
      >
        <div className="rise flex flex-col items-center">
          <SpotifyLockup />
          <Wordmark className="mt-1 text-[clamp(30px,8.4vw,150px)]" />
          <p className="caps mt-5 max-w-[24ch] text-[clamp(17px,2.5vw,40px)] leading-[1.12]">
            Your friends. Their music. One very competitive quiz.
          </p>
        </div>

        <div className="rise mt-12 flex w-full max-w-xl flex-col items-stretch gap-4 [animation-delay:80ms] sm:flex-row sm:items-center">
          <Button onClick={create} disabled={busy} className="sm:flex-1">
            {busy ? "Opening room" : "Start a room"}
          </Button>
          <form
            onSubmit={join}
            className="flex flex-1 items-center gap-2 rounded-full border-2 border-cream/80 py-1 pl-6 pr-1 focus-within:border-cream"
          >
            <label htmlFor="code" className="sr-only">
              Room code
            </label>
            <input
              id="code"
              value={code}
              onChange={(e) =>
                setCode(e.target.value.replace(/[^a-zA-Z]/g, "").slice(0, 4))
              }
              placeholder="ROOM CODE"
              autoCapitalize="characters"
              autoComplete="off"
              className="caps min-w-0 flex-1 rounded-sm bg-transparent text-[15px] tracking-[0.2em] text-cream placeholder:text-cream/55 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cream"
            />
            <button className="press caps min-h-10 rounded-full bg-cream/15 px-5 text-[14px] hover:bg-cream hover:text-blue focus-visible:outline-2 focus-visible:outline-cream">
              Join
            </button>
          </form>
        </div>
      </Slide>

      <Slide
        tone="cream"
        corner={false}
        className="flex min-h-[70dvh] items-center px-6 py-20 sm:px-[12%]"
      >
        <p className="caps text-[clamp(28px,5.4vw,84px)] leading-[0.98] font-semibold">
          Music is personal.
          <Star className="mb-[0.3em] ml-1 inline-block h-[1.1em] w-[1.1em] text-mustard" />
          <br />
          Soundcheck makes it
          <br />
          s
          <Star className="-mx-[0.08em] inline-block h-[1.15em] w-[1.15em] align-[-0.3em] text-red" />
          cial
          <Arrow className="ml-[0.5em] inline-block h-[0.6em] w-[2.6em] align-middle text-green" />
        </p>
      </Slide>

      <Slide tone="red" className="px-6 py-16 sm:px-[12%] sm:py-24">
        <Wordmark
          stacked
          className="text-center text-[clamp(56px,9vw,140px)]"
        />
        <ol className="caps mx-auto mt-12 flex max-w-4xl flex-col gap-8 text-[clamp(18px,2.6vw,38px)] leading-[1.05]">
          <li className="flex gap-5">
            <span>1</span>Join a private room and connect Spotify accounts.
          </li>
          <li className="flex gap-5">
            <span>2</span>Soundcheck turns listening history and stats into
            questions.
          </li>
          <li className="flex gap-5">
            <span>3</span>Answer, earn points, and debate the results.
          </li>
        </ol>
        <div className="mt-14 flex justify-center pb-10 sm:pb-0">
          <Button onClick={create} disabled={busy}>
            Start a room
          </Button>
        </div>
      </Slide>
    </Page>
  );
}
