#!/usr/bin/env python3
"""Build the Dictionary of Yorùbá Foods page from the Lexique Pro export.

Reads the entries in Yoruba-lexicon/lexicon/*.htm and writes
Yoruba-lexicon/index.html, styled to match the homepage.

Re-run after every new Lexique Pro export:

    python3 scripts/build_lexicon.py
"""
import html
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
LEX_DIR = ROOT / "Yoruba-lexicon"
OUT = LEX_DIR / "index.html"

# Yorùbá alphabet, used for the A–Z filter (gb before g so it matches first)
ALPHABET = ["a", "b", "d", "e", "ẹ", "f", "g", "gb", "h", "i", "j", "k", "l",
            "m", "n", "o", "ọ", "p", "r", "s", "ṣ", "t", "u", "w", "y"]

ENTRY_RE = re.compile(
    r'<p class="lpLexEntryPara[^"]*">(.*?)</p>\s*(?:<p class="lpPicturePara">(.*?)</p>)?',
    re.S,
)


def text(fragment):
    """Strip tags and decode entities."""
    s = html.unescape(re.sub(r"<[^>]+>", "", fragment or ""))
    return unicodedata.normalize("NFC", s.replace("\xa0", " ")).strip()


def spans(block, cls):
    return [text(m) for m in re.findall(rf'<span[^>]*class="{cls}"[^>]*>(.*?)</span>', block, re.S)]


def media_url(path):
    """'../audio/ata ewa.wav' -> 'audio/ata%20ewa.wav' (relative to Yoruba-lexicon/)."""
    path = unquote(html.unescape(path)).replace("../", "", 1)
    return quote(path)


def has_content(path):
    """False for missing or empty (failed upload) media files."""
    f = LEX_DIR / unquote(media_url(path))
    return f.is_file() and f.stat().st_size > 0


def letter_of(word):
    base = "".join(c for c in unicodedata.normalize("NFD", word.lower())
                   if c not in "̀́̄")
    base = unicodedata.normalize("NFC", base)
    for letter in sorted(ALPHABET, key=len, reverse=True):
        if base.startswith(letter):
            return letter
    return base[:1]


def parse():
    entries = []
    for page in sorted(LEX_DIR.glob("lexicon/[0-9][0-9].htm")):
        src = page.read_text(encoding="utf-8-sig")
        for block, picture in ENTRY_RE.findall(src):
            name = spans(block, "lpLexEntryName")
            if not name:
                continue
            audio = re.search(r"""(?:playAudio\('|href=")(\.\./audio/[^'"]+)""", block)
            img = re.search(r'src="(\.\./pictures/[^"]+)"', picture or "")
            if img and not has_content(img.group(1)):
                img = None
            glosses = spans(block, "lpGlossEnglish")
            examples = spans(block, "lpExample")
            entries.append({
                "word": name[0],
                "pos": (spans(block, "lpPartOfSpeech") or [""])[0],
                "ipa": (spans(block, "lpPhonetic") or [""])[0],
                "gloss": glosses[0] if glosses else "",
                "example": examples[0] if examples else "",
                "translation": glosses[1] if len(glosses) > 1 else "",
                "audio": media_url(audio.group(1)) if audio else "",
                "picture": media_url(img.group(1)) if img else "",
            })
    entries.sort(key=lambda e: unicodedata.normalize("NFD", e["word"].lower()))
    for e in entries:
        e["letter"] = letter_of(e["word"])
    return entries


def esc(s):
    return html.escape(s, quote=True)


def card(e):
    search = " ".join([e["word"], e["gloss"], e["example"], e["translation"]])
    pic = (f'<img src="{e["picture"]}" alt="{esc(e["word"])}" loading="lazy">'
           if e["picture"] else '<div class="no-pic">No picture yet</div>')
    play = (f'<button class="play" type="button" data-src="{e["audio"]}" '
            f'aria-label="Play pronunciation of {esc(e["word"])}">'
            '<svg class="i-play" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'
            '<svg class="i-stop" viewBox="0 0 24 24"><path d="M7 7h10v10H7z"/></svg>'
            '</button>') if e["audio"] else ""
    example = ""
    if e["example"]:
        example = (f'<blockquote class="example"><span lang="yo">{esc(e["example"])}</span>'
                   + (f'<span class="tr">{esc(e["translation"])}</span>' if e["translation"] else "")
                   + "</blockquote>")
    return f"""      <article class="entry" data-letter="{esc(e["letter"])}" data-search="{esc(search)}">
        <div class="pic">{pic}</div>
        <div class="body">
          <div class="head">
            <h3 lang="yo">{esc(e["word"])}</h3>
            {play}
          </div>
          <div class="meta"><span class="pos">{esc(e["pos"].rstrip(". ") or "n")}.</span> <span class="ipa">{esc(e["ipa"])}</span></div>
          <p class="gloss">{esc(e["gloss"])}</p>
          {example}
        </div>
      </article>"""


def build():
    entries = parse()
    used = {e["letter"] for e in entries}
    chips = ['<button class="chip active" type="button" data-letter="">All</button>']
    for letter in ALPHABET:
        if letter in used:
            chips.append(f'<button class="chip" type="button" data-letter="{letter}">{letter.upper() if len(letter) == 1 else letter.capitalize()}</button>')
    recordings = sum(1 for e in entries if e["audio"])
    page = TEMPLATE.format(
        count=len(entries),
        recordings=recordings,
        letters=len(used),
        chips="\n        ".join(chips),
        cards="\n".join(card(e) for e in entries),
    )
    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(entries)} entries")


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dictionary of Yorùbá Foods | Abíóyè Ọpẹ́yẹmí</title>
<meta name="description" content="An illustrated dictionary of Yorùbá foods and dishes, with tone-marked headwords, IPA transcriptions, example sentences and native-speaker audio.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Noto+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<!-- Generated by scripts/build_lexicon.py from the Lexique Pro export. Edit the script, not this file. -->
<style>
  :root {{
    --indigo: #1f2a5a;
    --indigo-2: #2d3b7a;
    --gold: #d99a26;
    --gold-dark: #b97f14;
    --clay: #b5502d;
    --cream: #faf6ee;
    --paper: #ffffff;
    --ink: #22252f;
    --muted: #5f6475;
    --line: #e7e1d4;
    --green: #2f8a57;
    --radius: 14px;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0;
    font-family: 'Noto Sans', 'Segoe UI', sans-serif;
    color: var(--ink);
    background: var(--cream);
    line-height: 1.6;
  }}
  a {{ color: inherit; }}
  h1, h2, h3 {{ font-family: 'Fraunces', Georgia, serif; line-height: 1.2; margin: 0; }}
  .wrap {{ max-width: 1100px; margin: 0 auto; padding: 0 16px; }}

  /* Nav */
  header.nav {{
    position: sticky; top: 0; z-index: 50;
    background: rgba(31, 42, 90, 0.97);
    color: #fff;
  }}
  .nav-inner {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; height: 60px; }}
  .brand {{ font-family: 'Fraunces', serif; font-weight: 700; font-size: 1.15rem; text-decoration: none; white-space: nowrap; }}
  .brand span {{ color: var(--gold); }}
  .nav-links {{ display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; }}
  .nav-links::-webkit-scrollbar {{ display: none; }}
  .nav-links a {{
    text-decoration: none; font-size: 0.92rem; padding: 6px 10px; border-radius: 8px;
    color: #dfe3f5; white-space: nowrap;
  }}
  .nav-links a:hover {{ background: rgba(255,255,255,0.1); color: #fff; }}
  .nav-links a.cta {{ background: var(--gold); color: var(--indigo); font-weight: 600; }}
  .nav-links a.cta:hover {{ background: #e8ab3a; }}

  /* Hero */
  .hero {{
    background:
      radial-gradient(circle at 85% 20%, rgba(217,154,38,0.25), transparent 40%),
      linear-gradient(135deg, var(--indigo) 0%, var(--indigo-2) 100%);
    color: #fff;
    padding: 56px 0 60px;
    position: relative;
    overflow: hidden;
  }}
  .hero::after {{
    /* adire-style dotted pattern */
    content: ""; position: absolute; inset: 0;
    background-image: radial-gradient(rgba(255,255,255,0.08) 1.5px, transparent 1.5px);
    background-size: 22px 22px;
    pointer-events: none;
  }}
  .hero .wrap {{ position: relative; z-index: 1; }}
  .crumb {{ font-size: 0.88rem; color: #c9cfe8; margin-bottom: 14px; }}
  .crumb a {{ color: #fff; text-decoration: none; }}
  .crumb a:hover {{ text-decoration: underline; }}
  .eyebrow {{ color: var(--gold); font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.82rem; }}
  .hero h1 {{ font-size: clamp(2.1rem, 5vw, 3.4rem); margin: 10px 0 16px; max-width: 760px; }}
  .hero p.lead {{ font-size: 1.12rem; color: #d6dbf0; max-width: 640px; margin: 0; }}
  .stats {{ display: flex; flex-wrap: wrap; gap: 28px; margin-top: 32px; color: #d6dbf0; font-size: 0.92rem; }}
  .stats strong {{ display: block; font-family: 'Fraunces', serif; font-size: 1.6rem; color: #fff; }}

  /* Search + letter filter */
  .toolbar {{
    position: sticky; top: 60px; z-index: 40;
    background: var(--paper); border-bottom: 1px solid var(--line);
    padding: 14px 0;
  }}
  .search {{
    width: 100%; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--line);
    font-size: 1.02rem; font-family: inherit; background: var(--cream); color: var(--ink);
  }}
  .search:focus {{ outline: 2px solid var(--gold); outline-offset: 1px; }}
  .chips {{ display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; margin-top: 10px; }}
  .chips::-webkit-scrollbar {{ display: none; }}
  .chip {{
    flex-shrink: 0; min-width: 38px; padding: 6px 10px; border-radius: 99px;
    border: 1px solid var(--line); background: var(--paper); color: var(--indigo);
    font: 600 0.9rem 'Noto Sans', sans-serif; cursor: pointer;
  }}
  .chip:hover {{ border-color: var(--gold); }}
  .chip.active {{ background: var(--indigo); border-color: var(--indigo); color: #fff; }}

  /* Entries */
  section {{ padding: 40px 0 64px; }}
  .count {{ color: var(--muted); font-size: 0.92rem; margin: 0 0 18px; }}
  .grid {{ display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  .entry {{
    background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius);
    overflow: hidden; display: flex; flex-direction: column;
    transition: box-shadow .2s, transform .2s;
  }}
  .entry:hover {{ box-shadow: 0 8px 24px rgba(31,42,90,0.09); transform: translateY(-2px); }}
  .entry[hidden] {{ display: none; }}
  .pic {{ position: relative; aspect-ratio: 4 / 3; overflow: hidden; background: #efe8d8; }}
  .pic img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }}
  .no-pic {{ height: 100%; display: grid; place-items: center; color: #8d8574; font-size: 0.85rem; }}
  .body {{ padding: 18px 20px 20px; display: flex; flex-direction: column; gap: 6px; }}
  .head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
  .entry h3 {{ font-size: 1.35rem; color: var(--indigo); }}
  .play {{
    flex-shrink: 0; width: 40px; height: 40px; border-radius: 50%; border: none; cursor: pointer;
    background: var(--gold); color: var(--indigo); display: grid; place-items: center;
    transition: transform .15s, background .15s;
  }}
  .play:hover {{ background: #e8ab3a; transform: scale(1.06); }}
  .play svg {{ width: 18px; height: 18px; fill: currentColor; }}
  .play .i-stop, .play.playing .i-play {{ display: none; }}
  .play.playing .i-stop {{ display: block; }}
  .play.playing {{ background: var(--indigo); color: #fff; }}
  .meta {{ font-size: 0.9rem; color: var(--muted); }}
  .pos {{ color: var(--clay); font-weight: 700; font-style: italic; }}
  .ipa {{ font-family: 'Noto Sans', 'Charis SIL', 'Doulos SIL', serif; }}
  .gloss {{ margin: 4px 0 0; }}
  .example {{
    margin: 8px 0 0; padding: 10px 14px; border-left: 3px solid var(--gold);
    background: var(--cream); border-radius: 0 8px 8px 0; font-size: 0.93rem;
  }}
  .example span {{ display: block; }}
  .example [lang="yo"] {{ font-style: italic; }}
  .example .tr {{ color: var(--muted); }}
  .empty {{ text-align: center; color: var(--muted); padding: 40px 0; }}

  /* Contact */
  .contact {{
    background: linear-gradient(135deg, var(--clay), #8f3b1f); color: #fff;
    border-radius: var(--radius); padding: 40px 28px; text-align: center; margin-top: 48px;
  }}
  .contact h2 {{ font-size: clamp(1.6rem, 3.5vw, 2.2rem); margin-bottom: 8px; }}
  .contact p {{ color: #f6dccf; margin: 0 auto 24px; max-width: 560px; }}
  .btn-row {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }}
  .btn {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 12px 20px; border-radius: 10px; font-weight: 600; text-decoration: none;
    border: 2px solid transparent; transition: transform .15s, background .15s; font-size: 0.98rem;
  }}
  .btn:hover {{ transform: translateY(-2px); }}
  .btn-gold {{ background: var(--gold); color: var(--indigo); }}
  .btn-gold:hover {{ background: #e8ab3a; }}
  .btn-ghost {{ border-color: rgba(255,255,255,0.5); color: #fff; }}
  .btn-ghost:hover {{ background: rgba(255,255,255,0.1); }}

  footer {{ background: var(--indigo); color: #c9cfe8; padding: 28px 0; font-size: 0.88rem; }}
  .foot {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; }}
  footer a {{ color: #fff; }}
</style>
</head>
<body>

<!-- ============ NAVIGATION ============ -->
<header class="nav">
  <div class="wrap nav-inner">
    <a href="/" class="brand">Abíóyè <span>Ọpẹ́yẹmí</span></a>
    <nav class="nav-links">
      <a href="/#services">Services</a>
      <a href="/#tools">Tools</a>
      <a href="/#dictionaries">Dictionaries</a>
      <a href="/#learn">Learn</a>
      <a href="/#research">Research</a>
      <a href="/#work">Our Work</a>
      <a href="/#about">About</a>
      <a href="/#contact" class="cta">Hire Us</a>
    </nav>
  </div>
</header>

<!-- ============ HERO ============ -->
<div class="hero" id="top">
  <div class="wrap">
    <div class="crumb"><a href="/">Home</a> › <a href="/#dictionaries">Dictionaries</a> › Yorùbá Foods</div>
    <div class="eyebrow">Dictionary · Yorùbá · Food</div>
    <h1>Dictionary of Yorùbá Foods</h1>
    <p class="lead">Names of Yorùbá foods and dishes, with tone-marked spellings, IPA transcriptions, example sentences, pictures and native-speaker recordings.</p>
    <div class="stats">
      <div><strong>{count}</strong>Entries</div>
      <div><strong>{recordings}</strong>Audio recordings</div>
      <div><strong>{letters}</strong>Letters</div>
    </div>
  </div>
</div>

<!-- ============ SEARCH ============ -->
<div class="toolbar">
  <div class="wrap">
    <input class="search" id="search" type="search" placeholder="Search in Yorùbá or English, e.g. ẹ̀bà, eba, beans…" aria-label="Search the dictionary">
    <div class="chips" id="chips" role="group" aria-label="Filter by letter">
        {chips}
    </div>
  </div>
</div>

<!-- ============ ENTRIES ============ -->
<section>
  <div class="wrap">
    <p class="count" id="count" aria-live="polite"></p>
    <div class="grid" id="entries">
{cards}
    </div>
    <p class="empty" id="empty" hidden>No entries match your search.</p>

    <div class="contact">
      <h2>Need Yorùbá language work?</h2>
      <p>Transcription, annotation, translation and editing by a Yorùbá linguist.</p>
      <div class="btn-row">
        <a href="mailto:abioye1718@gmail.com?subject=Project%20enquiry" class="btn btn-gold">Email Us</a>
        <a href="https://wa.me/2349025534185" class="btn btn-ghost">Chat on WhatsApp</a>
      </div>
    </div>
  </div>
</section>

<footer>
  <div class="wrap foot">
    <div>© <span id="year"></span> Abíóyè Ọpẹ́yẹmí · Linguistics Hub</div>
    <div><a href="mailto:abioye1718@gmail.com">abioye1718@gmail.com</a></div>
  </div>
</footer>

<script>
  document.getElementById("year").textContent = new Date().getFullYear();

  // ---------- Search and letter filter ----------
  // Ignore tone marks and under-dots so "eba" finds "Ẹ̀bà"
  const fold = s => s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
  const entries = [...document.querySelectorAll(".entry")];
  entries.forEach(e => e.dataset.fold = fold(e.dataset.search));
  const search = document.getElementById("search");
  const chips = [...document.querySelectorAll(".chip")];
  const count = document.getElementById("count");
  const empty = document.getElementById("empty");
  let letter = "";

  function filter() {{
    const q = fold(search.value.trim());
    let shown = 0;
    for (const e of entries) {{
      const ok = (!letter || e.dataset.letter === letter) && (!q || e.dataset.fold.includes(q));
      e.hidden = !ok;
      if (ok) shown++;
    }}
    count.textContent = shown === entries.length
      ? `Showing all ${{shown}} entries`
      : `Showing ${{shown}} of ${{entries.length}} entries`;
    empty.hidden = shown > 0;
  }}

  search.addEventListener("input", filter);
  chips.forEach(chip => chip.addEventListener("click", () => {{
    chips.forEach(c => c.classList.toggle("active", c === chip));
    letter = chip.dataset.letter;
    filter();
  }}));
  filter();

  // ---------- Audio ----------
  const player = new Audio();
  let current = null;
  function stop() {{
    if (current) current.classList.remove("playing");
    current = null;
  }}
  player.addEventListener("ended", stop);
  player.addEventListener("error", stop);
  document.querySelectorAll(".play").forEach(btn => btn.addEventListener("click", () => {{
    const same = current === btn;
    player.pause();
    stop();
    if (same) return;
    player.src = btn.dataset.src;
    player.play().catch(stop);
    current = btn;
    btn.classList.add("playing");
  }}));
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
