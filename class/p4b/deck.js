// Wrap each slide in a frame and scale it to the frame's width.
for (const slide of document.querySelectorAll("#deck > .slide")) {
  const frame = document.createElement("div");
  frame.className = "frame";
  frame.id = `s${slide.dataset.n}`;
  slide.before(frame);
  frame.appendChild(slide);
}
const fit = () => {
  for (const frame of document.querySelectorAll(".frame")) {
    frame.firstElementChild.style.transform = `scale(${frame.clientWidth / 1456})`;
  }
};
addEventListener("resize", fit);
fit();

// Open items: every unfilled marker, linked to its slide.
const list = document.getElementById("todo-list");
const needs = [...document.querySelectorAll(".need")];
for (const el of needs) {
  const li = document.createElement("li");
  const a = document.createElement("a");
  const n = el.closest(".slide").dataset.n;
  a.href = `#s${n}`;
  a.textContent = `Slide ${n}`;
  li.append(a, `: ${el.textContent.trim()}`);
  list.appendChild(li);
}
if (!needs.length) document.querySelector(".todo").remove();

// ?slide=N shows one slide at its native 1456x819, unscaled, so the PDF can
// be built from screenshots of exactly what the site draws. Chrome's print
// path flattens blurred shadows into solid blocks (the saber glow), which is
// why the printed PDF didn't match the site.
const only = new URLSearchParams(location.search).get("slide");
if (only) {
  document.querySelector(".todo")?.remove();
  document.body.style.background = "none";
  const deck = document.getElementById("deck");
  deck.style.cssText = "padding:0;gap:0;display:block;max-width:none;margin:0";
  for (const frame of document.querySelectorAll(".frame")) {
    if (frame.id !== `s${only}`) { frame.remove(); continue; }
    frame.style.cssText = "width:1456px;height:819px;aspect-ratio:auto";
    frame.firstElementChild.style.transform = "none";
  }
}
