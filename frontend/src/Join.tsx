import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Creds, type RoomState } from "./api";
import {
  forgetPass,
  loadPass,
  passAge,
  savePass,
  type Pass,
  type Profile,
  type Source,
} from "./profiles";
import { TasteBuilder } from "./Taste";
import { Avatar, Button, Page, Slide, Star, Wordmark } from "./ui";

const READS = [
  {
    scope: "Top tracks and artists",
    detail: "Your last 4 weeks and last 12 months. Every question starts here.",
  },
  {
    scope: "Recently played",
    detail:
      "Your last 50 plays and what hour they happened. Powers the on-repeat, last-song and late-night questions.",
  },
];
const NEVER = [
  "Your playlists, likes or follows",
  "Your email, password or payment info",
  "Playing, pausing or changing anything",
];

export const SOURCE_LABEL: Record<Source, string> = {
  picks: "Quick picks",
  export: "Spotify data upload",
  spotify: "Spotify login",
  sample: "Sample listener",
};

type JoinProps = {
  code: string;
  state: RoomState;
  onJoined: (c: Creds) => void;
  onError: (m: string) => void;
};

export function Join({ code, state, onJoined, onError }: JoinProps) {
  const [pass, setPass] = useState<Pass | null>(() => loadPass());
  const [name, setName] = useState(() => loadPass()?.name ?? "");
  const [busy, setBusy] = useState(false);
  const [recent, setRecent] = useState(true);
  const [health, setHealth] = useState({ spotify: false, search: true });
  const [builder, setBuilder] = useState<"picks" | "export" | null>(null);
  const [showSpotify, setShowSpotify] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.health().then(
      (h) => setHealth({ spotify: h.spotify, search: h.search }),
      () => setHealth({ spotify: false, search: false }),
    );
    if (!loadPass() && window.matchMedia("(pointer: fine)").matches)
      inputRef.current?.focus();
  }, []);

  const started = state.phase !== "lobby";
  const named = name.trim().length > 0;

  async function joinWith(
    source: Source,
    profile: Profile,
    through?: string,
    avatar: string | null = null,
    who = name.trim(),
  ) {
    if (!who) {
      onError("Add your name first.");
      return;
    }
    setBusy(true);
    try {
      const c = await api.joinProfile(code, who, source, profile, avatar);
      savePass({
        name: who,
        avatar,
        source,
        profile,
        saved: Date.now(),
        through,
      });
      onJoined(c);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Couldn't join.");
      setBusy(false);
    }
  }

  async function sample() {
    if (!named) return;
    setBusy(true);
    try {
      onJoined(await api.joinSample(code, name.trim(), recent));
    } catch (e) {
      onError(e instanceof Error ? e.message : "Couldn't join.");
      setBusy(false);
    }
  }

  function spotify(e: FormEvent) {
    e.preventDefault();
    if (!named || !health.spotify) return;
    setBusy(true);
    window.location.href = api.loginUrl(code, name.trim(), recent);
  }

  return (
    <Page>
      <Slide
        tone="red"
        className="flex min-h-[calc(100dvh-24px)] flex-col justify-center px-6 py-16 sm:min-h-[calc(100dvh-48px)] sm:px-[10%]"
      >
        <div className="rise flex flex-col gap-10 lg:flex-row lg:items-start lg:justify-between lg:gap-16">
          <div className="min-w-0 lg:pt-24">
            <p className="caps text-[clamp(14px,1.5vw,20px)] opacity-80">
              Room
            </p>
            <p className="display text-[clamp(64px,9vw,150px)] tracking-[0.04em]">
              {code}
            </p>
            {state.players.length > 0 ? (
              <div className="mt-5 flex items-center gap-3">
                <div className="flex -space-x-3">
                  {state.players.slice(0, 6).map((p, i) => (
                    <Avatar
                      key={p.id}
                      name={p.name}
                      src={p.avatar}
                      index={i}
                      className="h-11 w-11 text-[20px] ring-4 ring-red"
                    />
                  ))}
                </div>
                <p className="caps text-[clamp(15px,1.5vw,20px)]">
                  {state.players.length === 1
                    ? `${state.players[0].name} is here`
                    : `${state.players.length} friends are here`}
                </p>
              </div>
            ) : (
              <p className="caps mt-3 text-[clamp(15px,1.6vw,22px)]">
                You're first in.
              </p>
            )}
            {state.season && state.season.games > 0 && (
              <p className="caps mt-4 text-[14px] opacity-85">
                {state.season.games}{" "}
                {state.season.games === 1 ? "game" : "games"} played here.{" "}
                {state.season.table[0]?.name} leads the season.
              </p>
            )}
          </div>

          <form
            onSubmit={spotify}
            className="flex w-full min-w-0 max-w-lg flex-col gap-6 lg:shrink-0"
          >
            <Wordmark stacked className="text-[clamp(44px,5vw,76px)]" />

            {started ? (
              <p className="caps text-[18px]">
                This game already started. Hang tight for the rematch.
              </p>
            ) : pass && !builder ? (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4 rounded-md border-2 border-cream p-4">
                  <Avatar
                    name={pass.name}
                    src={pass.avatar}
                    className="h-14 w-14 text-[26px]"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-cond text-[34px] uppercase leading-none">
                      {pass.name}
                    </p>
                    <p className="mt-1 font-mono text-[12px] opacity-80">
                      {SOURCE_LABEL[pass.source]} / saved {passAge(pass)}
                      {pass.through ? ` / plays through ${pass.through}` : ""}
                    </p>
                    <p className="mt-1 truncate text-[13px] opacity-80">
                      {pass.profile.top_artists_long
                        .slice(0, 3)
                        .map((a) => a.name)
                        .join(", ")}
                    </p>
                  </div>
                </div>
                <Button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    joinWith(
                      pass.source,
                      pass.profile,
                      pass.through,
                      pass.avatar,
                      pass.name,
                    )
                  }
                >
                  {busy ? "Joining" : `Join as ${pass.name}`}
                </Button>
                <div className="flex flex-wrap gap-x-5 gap-y-2">
                  <button
                    type="button"
                    onClick={() => setPass(null)}
                    className="press caps text-[13px] underline underline-offset-4 opacity-80 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
                  >
                    Use different taste
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      forgetPass();
                      setPass(null);
                      setName("");
                    }}
                    className="press caps text-[13px] underline underline-offset-4 opacity-80 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream"
                  >
                    Forget me on this phone
                  </button>
                </div>
              </div>
            ) : (
              <>
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
                    enterKeyHint="next"
                    className="caps rounded-sm border-b-[3px] border-cream/70 bg-transparent pb-2 text-[clamp(26px,3vw,40px)] text-cream placeholder:text-cream/40 focus-visible:border-cream focus-visible:outline-1 focus-visible:outline-offset-8 focus-visible:outline-cream/40"
                  />
                </label>
                <span className="caps -mb-3 text-[14px] opacity-80">
                  2 &nbsp;Bring your taste
                </span>

                {builder ? (
                  <TasteBuilder
                    kind={builder}
                    onCancel={() => setBuilder(null)}
                    onDone={(r) => joinWith(r.source, r.profile, r.through)}
                  />
                ) : (
                  <div className="flex flex-col gap-3">
                    {health.search && (
                      <SourceButton
                        disabled={!named || busy}
                        onClick={() => setBuilder("picks")}
                        title="Quick picks"
                        line="Search and pick your top artists and songs. About a minute."
                        primary
                      />
                    )}
                    {health.search && (
                      <SourceButton
                        disabled={!named || busy}
                        onClick={() => setBuilder("export")}
                        title="Upload Spotify data"
                        line="Your real year of listening, read on this phone. Most accurate."
                      />
                    )}
                    {health.spotify && (
                      <SourceButton
                        disabled={!named || busy}
                        onClick={() => setShowSpotify(!showSpotify)}
                        title="Spotify login"
                        line="Invite-only beta: Spotify allows 5 accounts until SoundCheck is approved."
                      />
                    )}
                    {showSpotify && health.spotify && (
                      <div className="rounded-md border-2 border-cream/40 p-4">
                        <ul className="flex flex-col gap-3 text-[14px] leading-snug">
                          {READS.map((r, i) => (
                            <li
                              key={r.scope}
                              className="flex items-start gap-3"
                            >
                              {i === 1 ? (
                                <input
                                  id="recent"
                                  type="checkbox"
                                  checked={recent}
                                  onChange={(e) => setRecent(e.target.checked)}
                                  className="mt-0.5 h-5 w-5 shrink-0 accent-cream focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream"
                                />
                              ) : (
                                <Star className="mt-0.5 h-5 w-5 shrink-0" />
                              )}
                              <label
                                htmlFor={i === 1 ? "recent" : undefined}
                                className={i === 1 ? "cursor-pointer" : ""}
                              >
                                <span className="caps block">
                                  {r.scope}
                                  {i === 0 ? " (required)" : ""}
                                </span>
                                <span className="opacity-80">{r.detail}</span>
                              </label>
                            </li>
                          ))}
                        </ul>
                        <p className="caps mt-4 text-[12px] opacity-75">
                          Never: {NEVER.join(" / ")}
                        </p>
                        <Button
                          type="submit"
                          disabled={!named || busy}
                          className="mt-4 w-full"
                        >
                          {busy ? "Opening Spotify" : "Continue to Spotify"}
                        </Button>
                      </div>
                    )}
                    <button
                      type="button"
                      disabled={!named || busy}
                      onClick={sample}
                      className="press caps self-start text-[13px] underline underline-offset-4 opacity-80 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-cream disabled:opacity-40"
                    >
                      Just trying it? Use a sample listener
                    </button>
                  </div>
                )}
              </>
            )}
            <p className="font-mono text-[12px] leading-relaxed opacity-75">
              Your taste saves on this phone so next game is one tap. The room
              keeps it while you're in it: leave and it's deleted, and rooms
              clear out after 30 quiet days.
            </p>
          </form>
        </div>
      </Slide>
    </Page>
  );
}

function SourceButton({
  title,
  line,
  onClick,
  disabled,
  primary = false,
}: {
  title: string;
  line: string;
  onClick: () => void;
  disabled: boolean;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`press flex items-center justify-between gap-4 rounded-md border-2 px-4 py-3.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cream disabled:cursor-not-allowed disabled:opacity-45 ${
        primary
          ? "border-cream bg-cream text-ink hover:bg-paper"
          : "border-cream/50 hover:border-cream"
      }`}
    >
      <span>
        <span className="caps block text-[15px]">{title}</span>
        <span className="block text-[13px] leading-snug opacity-80">
          {line}
        </span>
      </span>
      <span aria-hidden className="text-[20px]">
        &rarr;
      </span>
    </button>
  );
}
