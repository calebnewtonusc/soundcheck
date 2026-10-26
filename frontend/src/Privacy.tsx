import { go } from "./App";
import { Button, Page, Slide, Wordmark } from "./ui";

const SECTIONS: { title: string; lines: string[] }[] = [
  {
    title: "What we read",
    lines: [
      "Connect Spotify (stats.fm): the top tracks, top artists, genres and last 50 plays on your public stats.fm profile. We never see your stats.fm or Spotify login.",
      "Spotify sign-in: your top tracks and artists, and your last 50 plays if you leave that box ticked. We use the access once, then drop it.",
      "Spotify data upload: the file is read on your phone. Only your top songs, top artists and last 50 plays are sent.",
      "Quick picks: just what you pick.",
    ],
  },
  {
    title: "Where it lives",
    lines: [
      "Your taste is kept in the room you join, so the questions can be written. Leave the room and your data and season stats are deleted. A room nobody has used for 30 days is deleted.",
      "Your phone keeps a copy so the next game is one tap. Forget me on this phone deletes it.",
      "If the host turns on AI wording, the question text (names and song titles) goes to Anthropic's Claude to be reworded. Nothing else does.",
    ],
  },
  {
    title: "What we never do",
    lines: [
      "No ads. No selling or sharing your data. No posting anywhere for you. No playing, pausing or changing anything on your account.",
    ],
  },
  {
    title: "Terms",
    lines: [
      "SoundCheck is a free game made for fun, offered as is. It isn't made by or affiliated with Spotify or stats.fm.",
      "Keep names and room chat friendly. Hosts can remove anyone from their room.",
      "Questions or a delete request: open an issue at github.com/calebnewtonusc/soundcheck.",
    ],
  },
];

export function Privacy() {
  return (
    <Page>
      <Slide tone="cream" className="px-6 py-14 sm:px-[10%] sm:py-20">
        <Wordmark className="text-[clamp(34px,5vw,64px)] text-blue" />
        <h1 className="display mt-8 text-[clamp(32px,5vw,72px)] text-blue">
          Privacy and terms
        </h1>
        <p className="mt-4 max-w-2xl text-[16px] leading-relaxed text-ink/80">
          The short version: we read only what makes the quiz work, keep it only
          while you play, and never sell it.
        </p>
        <div className="mt-12 grid gap-10 lg:grid-cols-2">
          {SECTIONS.map((s) => (
            <section key={s.title}>
              <h2 className="font-cond text-[clamp(28px,3vw,40px)] uppercase leading-none text-red">
                {s.title}
              </h2>
              <ul className="mt-4 flex flex-col gap-3 text-[15px] leading-relaxed text-ink">
                {s.lines.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        <p className="mt-12 font-mono text-[12px] text-ink/60">
          Updated October 26, 2026
        </p>
        <Button tone="ink" onClick={() => go("/")} className="mt-8">
          Back to SoundCheck
        </Button>
      </Slide>
    </Page>
  );
}
