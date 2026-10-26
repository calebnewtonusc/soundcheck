import { useCallback, useEffect, useState } from "react";
import { Button, Page, Slide, Star, Wordmark } from "./ui";

type Request = {
  email: string;
  name: string;
  room: string | null;
  status: "pending" | "added" | "declined";
  created_at: string;
};
type Data = {
  requests: Request[];
  spots_total: number;
  spots_used: number;
  dashboard: string;
};

// The key rides in the URL hash so it never reaches server logs or referrers.
const key = () => decodeURIComponent(window.location.hash.replace(/^#/, ""));

export function Admin() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  const load = useCallback(async () => {
    const res = await fetch(
      `/api/admin/access?${new URLSearchParams({ key: key() })}`,
    );
    if (!res.ok) {
      setError(
        res.status === 404
          ? "This link isn't valid."
          : "Couldn't load requests.",
      );
      return;
    }
    setData((await res.json()) as Data);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function mark(email: string, status: Request["status"]) {
    const res = await fetch("/api/admin/access", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: key(), email, status }),
    });
    if (res.ok) setData((await res.json()) as Data);
    else setError("Couldn't save that.");
  }

  async function copy(email: string) {
    try {
      await navigator.clipboard.writeText(email);
      setCopied(email);
      window.setTimeout(() => setCopied(""), 1500);
    } catch {
      setCopied("");
    }
  }

  const pending = data?.requests.filter((r) => r.status === "pending") ?? [];
  const added = data?.requests.filter((r) => r.status === "added") ?? [];
  const full = data ? data.spots_used >= data.spots_total : false;

  return (
    <Page>
      <Slide
        tone="ink"
        className="min-h-[calc(100dvh-24px)] px-6 py-12 ring-1 ring-cream/10 sm:min-h-[calc(100dvh-48px)] sm:px-[8%] sm:py-16"
      >
        <Wordmark className="text-[clamp(36px,5vw,64px)]" />
        <p className="caps mt-3 text-[15px] opacity-80">
          Spotify sign-in spots
        </p>

        {error && <p className="caps mt-10 text-[18px]">{error}</p>}
        {!data && !error && (
          <Star className="spin-slow mt-10 h-14 w-14 text-cream" />
        )}

        {data && (
          <div className="mt-8 grid gap-12 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)]">
            <div className="flex flex-col gap-5">
              <p className="font-cond text-[clamp(90px,12vw,170px)] leading-none">
                {data.spots_used}/{data.spots_total}
              </p>
              <p className="text-[16px] leading-snug opacity-85">
                {full
                  ? "Every spot is taken. New friends get quick picks automatically."
                  : `${data.spots_total - data.spots_used} open. Your own account uses the first.`}
              </p>
              <a
                href={data.dashboard}
                target="_blank"
                rel="noreferrer"
                className="press caps inline-flex min-h-12 items-center justify-center rounded-full bg-cream px-7 text-[15px] text-ink hover:bg-paper focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cream"
              >
                Open Spotify's user list &rarr;
              </a>
              <ol className="flex flex-col gap-2 text-[14px] leading-snug opacity-85">
                <li>1. Copy a friend's email below.</li>
                <li>
                  2. In Spotify's user list, paste their name and email, then
                  Add user.
                </li>
                <li>
                  3. Come back and tap Added. They can sign in right away.
                </li>
              </ol>
            </div>

            <div className="flex flex-col gap-8">
              <section>
                <p className="caps text-[14px] opacity-80">
                  Waiting ({pending.length})
                </p>
                {pending.length === 0 ? (
                  <p className="mt-3 text-[15px] opacity-70">
                    No one's asking right now. When a friend's Spotify sign-in
                    is turned away, they show up here.
                  </p>
                ) : (
                  <ul className="mt-3 flex flex-col gap-3">
                    {pending.map((r) => (
                      <li
                        key={r.email}
                        className="flex flex-col gap-3 rounded-md border border-cream/25 p-4 sm:flex-row sm:items-center"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-cond text-[28px] uppercase leading-none">
                            {r.name}
                          </p>
                          <p className="mt-1 truncate font-mono text-[13px] opacity-80">
                            {r.email}
                            {r.room ? ` / room ${r.room}` : ""}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="ghost"
                            className="min-h-10 px-4 text-[13px]"
                            onClick={() => copy(r.email)}
                          >
                            {copied === r.email ? "Copied" : "Copy email"}
                          </Button>
                          <Button
                            className="min-h-10 px-4 text-[13px]"
                            disabled={full}
                            onClick={() => mark(r.email, "added")}
                          >
                            Added
                          </Button>
                          <button
                            onClick={() => mark(r.email, "declined")}
                            className="press caps px-2 text-[12px] underline underline-offset-4 opacity-70 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
                          >
                            Skip
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              {added.length > 0 && (
                <section>
                  <p className="caps text-[14px] opacity-80">
                    On the list ({added.length})
                  </p>
                  <ul className="mt-3 flex flex-col gap-2">
                    {added.map((r) => (
                      <li
                        key={r.email}
                        className="flex items-center justify-between gap-3 border-b border-cream/15 pb-2"
                      >
                        <span className="min-w-0 truncate text-[15px]">
                          {r.name}{" "}
                          <span className="font-mono text-[12px] opacity-70">
                            {r.email}
                          </span>
                        </span>
                        <button
                          onClick={() => mark(r.email, "pending")}
                          className="press caps shrink-0 text-[12px] underline underline-offset-4 opacity-70 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
                        >
                          Undo
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          </div>
        )}
      </Slide>
    </Page>
  );
}
