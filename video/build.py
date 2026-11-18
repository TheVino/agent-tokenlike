"""Writes the HyperFrames pages of the README videos and, with --render, renders them into docs/.

    python video/build.py [--lang en|pt] [--render]

en -> video/purpose, video/features -> docs/purpose.mp4, docs/features.mp4
pt -> video/purpose-pt, video/features-pt -> docs/purpose-pt.mp4, docs/features-pt.mp4
Record the clips first with `python tools/record_clips.py --lang <lang>` (they stay out of git).
Rendering needs Node and the HyperFrames CLI (`npx hyperframes`) plus ffmpeg (development only).
"""
import argparse, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / "docs"
BOX = (700, 40, 1180, 1000)        # footage area on the 1920x1080 frame
PET = (720, 590, 520, 480)         # regions in screen px of the 1280x1080 capture (clips are 2x)
CHOICE = (500, 590, 740, 480)

REG = {"tokens": PET, "fight": PET, "boss": PET, "chest": PET, "look": PET, "secret": PET,
       "idol": CHOICE, "campfire": CHOICE,
       "items": (30, 20, 622, 545), "synergies": (30, 20, 622, 545), "heroes": (30, 20, 700, 953),
       "journal": (30, 20, 476, 502), "graveyard": (30, 20, 520, 502), "profile": (30, 20, 350, 707),
       "achievements": (30, 20, 662, 1055), "stats": (30, 20, 458, 470)}
REG_LANG = {"pt": {"profile": (30, 20, 372, 707), "idol": (430, 590, 850, 480), "campfire": (430, 590, 850, 480)}}   # wider windows in Portuguese

SHOTS = {  # (clip, media start, seconds); the texts come from TEXT[lang]
    "purpose": [("tokens", 0.5, 5.0), ("fight", 0.5, 4.5), ("boss", 0.5, 4.5), ("chest", 0.5, 4.0), ("profile", 0.3, 3.5)],
    "features": [("fight", 1.0, 3.3), ("look", 0.3, 3.3), ("synergies", 0.3, 3.3), ("idol", 0.9, 3.3),
                 ("campfire", 0.9, 3.3), ("heroes", 0.3, 3.3), ("journal", 0.3, 3.0), ("profile", 0.3, 3.0)],
}
TEXT = {  # (title, subtitle) per shot, then the end card tagline
    "en": {
        "purpose": ([("Every token you spend", "in Claude Code feeds a tiny pixel pet"),
                     ("Energy opens rooms", "and the pet fights its way down a dungeon"),
                     ("A boss every 5 floors", "the dungeon is where the danger lives"),
                     ("Items stack on the pet", "and you can see every one of them"),
                     ("Your usage, at a glance", "today, streaks and your session limits")],
                    "a pixel pet for Claude Code"),
        "features": ([("Round-based combat", "speed, crits, burn, poison, shock, freeze"),
                      ("100 items that stack", "and show up on your pet"),
                      ("Synergies", "sets, named pairs, element reactions"),
                      ("Choices with a price", "the Cracked Idol trades HP for an epic item"),
                      ("Traveler's Campfire", "rest, hear a tale, pick a boon"),
                      ("20 heroes to unlock", "each with a trait, by achievements"),
                      ("Journal and Graveyard", "every tale heard, every run that fell"),
                      ("Profile and limits", "your Claude Code session and week, on the pet")],
                     "a pixel pet for Claude Code · open source"),
    },
    "pt": {   # game terms as in i18n.PT (Ídolo Rachado, Fogueira do Viajante, Diário, Cemitério...)
        "purpose": ([("Cada token que você gasta", "no Claude Code alimenta um pet de pixel"),
                     ("Energia abre salas", "e o pet desce uma masmorra lutando"),
                     ("Um chefe a cada 5 andares", "o perigo mora na masmorra"),
                     ("Itens se acumulam no pet", "e dá para ver cada um deles"),
                     ("Seu uso num relance", "hoje, dias seguidos e os limites da sessão")],
                    "um pet de pixel para o Claude Code"),
        "features": ([("Combate em rodadas", "velocidade, críticos, queimadura, veneno, eletricidade, congelamento"),
                      ("100 itens que se acumulam", "e aparecem no seu pet"),
                      ("Sinergias", "conjuntos, pares e reações de elementos"),
                      ("Escolhas com preço", "o Ídolo Rachado troca vida por um item épico"),
                      ("Fogueira do Viajante", "descanse, ouça uma história, escolha uma bênção"),
                      ("20 heróis para desbloquear", "cada um com seu traço, liberados por conquistas"),
                      ("Diário e Cemitério", "cada história ouvida, cada run que caiu"),
                      ("Perfil e limites", "sua sessão e semana do Claude Code, no pet")],
                     "um pet de pixel para o Claude Code · código aberto"),
    },
}
END = 3.2

CSS = """
:root { --ground: #13121e; --ink: #f4f1ff; --muted: #a9a4d6; --gold: #ffd23f; --font-display: "Outfit"; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1920px; height: 1080px; overflow: hidden; background: var(--ground); }
#root { width: 100%; height: 100%; position: relative; background: var(--ground); font-family: var(--font-display); }
.frame { position: absolute; left: 700px; top: 40px; width: 1180px; height: 1000px; overflow: hidden; }
.frame video { position: absolute; left: 0; top: 0; width: 2560px; height: 2160px; image-rendering: pixelated; transform-origin: 0 0; }
.copy { position: absolute; left: 110px; top: 0; width: 560px; height: 1080px; display: flex; flex-direction: column; justify-content: center; }
.copy .bar { width: 64px; height: 8px; background: var(--gold); margin-bottom: 28px; }
.copy h1 { color: var(--ink); font-size: 72px; font-weight: 700; line-height: 1.05; letter-spacing: -0.02em; }
.copy p { color: var(--muted); font-size: 34px; font-weight: 400; line-height: 1.3; margin-top: 22px; }
.end { position: absolute; left: 0; top: 560px; width: 1920px; display: flex; flex-direction: column; align-items: center; }
.end h1 { color: var(--ink); font-size: 128px; font-weight: 700; letter-spacing: -0.03em; }
.end h1 span { color: var(--gold); }
.end p { color: var(--muted); font-size: 40px; margin-top: 18px; }
.pet { position: absolute; left: 660px; top: 170px; width: 600px; height: 380px; overflow: hidden; }
.pet video { position: absolute; left: 0; top: 0; width: 2560px; height: 2160px; image-rendering: pixelated; transform-origin: 0 0; }
"""


def placement(clip, lang="en"):
    sx, sy, sw, sh = REG_LANG.get(lang, {}).get(clip, REG[clip])
    s = min(BOX[2] / sw, BOX[3] / sh)            # screen px -> frame px
    k = s / 2                                    # the clip is 2x the screen
    ox = (BOX[2] - sw * s) / 2 - sx * s
    oy = (BOX[3] - sh * s) / 2 - sy * s
    return f"transform: translate({ox:.1f}px, {oy:.1f}px) scale({k:.4f})"


def page(cid, shots, texts, tagline, lang):
    t, body, js = 0.0, [], []
    for i, ((clip, ms, d), (title, sub)) in enumerate(zip(shots, texts)):
        n = f"s{i + 1}"
        body.append(f"""
      <div class="frame" id="{n}-frame">
        <video id="{n}-video" class="clip" data-start="{t:.2f}" data-duration="{d:.2f}" data-media-start="{ms}"
               data-track-index="0" src="assets/clips/{clip}.mp4" muted playsinline style="{placement(clip, lang)}"></video>
      </div>
      <div id="{n}-copy" class="copy clip" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="1">
        <div id="{n}-bar" class="bar"></div>
        <h1 id="{n}-title">{title}</h1>
        <p id="{n}-sub">{sub}</p>
      </div>""")
        js.append(f"""    tl.fromTo("#{n}-bar", {{ scaleX: 0, transformOrigin: "0 50%" }}, {{ scaleX: 1, duration: 0.3, ease: "power3.out" }}, {t + 0.05:.2f});
    tl.fromTo("#{n}-title", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.45, ease: "power3.out" }}, {t + 0.1:.2f});
    tl.fromTo("#{n}-sub", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35, ease: "power2.out" }}, {t + 0.45:.2f});
    tl.fromTo("#{n}-frame", {{ scale: 1.0 }}, {{ scale: 1.03, duration: {d:.2f}, ease: "none", transformOrigin: "50% 60%" }}, {t:.2f});""")
        t += d
    pet = "transform: translate(-1180px, -1180px) scale(0.9)"   # the pet from look.mp4, centred in .pet
    body.append(f"""
      <div class="pet" id="end-pet">
        <video id="end-video" class="clip" data-start="{t:.2f}" data-duration="{END}" data-media-start="0.5"
               data-track-index="0" src="assets/clips/look.mp4" muted playsinline style="{pet}"></video>
      </div>
      <div id="end" class="end clip" data-start="{t:.2f}" data-duration="{END}" data-track-index="1">
        <h1 id="end-title">Agent <span>Token</span>like</h1>
        <p id="end-sub">{tagline}</p>
      </div>""")
    js.append(f"""    tl.fromTo("#end-pet", {{ y: 40, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.4, ease: "back.out(1.6)" }}, {t + 0.05:.2f});
    tl.fromTo("#end-title", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.5, ease: "power3.out" }}, {t + 0.3:.2f});
    tl.fromTo("#end-sub", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {t + 0.7:.2f});""")
    total = t + END
    return f"""<!doctype html>
<html lang="{"pt-BR" if lang == "pt" else "en"}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>{CSS}    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{cid}" data-start="0" data-duration="{total:.2f}" data-width="1920" data-height="1080">{"".join(body)}
    </div>
    <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
    window.__timelines["{cid}"] = tl;
    tl.seek(0);
    </script>
  </body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=("en", "pt"), default="en")
    ap.add_argument("--render", action="store_true", help="render with HyperFrames and write docs/<name>[-pt].mp4")
    a = ap.parse_args()
    suffix = "" if a.lang == "en" else "-" + a.lang
    for name in SHOTS:
        d = ROOT / (name + suffix)
        d.mkdir(exist_ok=True)
        for f in ("hyperframes.json", "package.json"):          # project files come from the English project
            if not (d / f).exists():
                shutil.copy(ROOT / name / f, d / f)
        texts, tag = TEXT[a.lang][name]
        (d / "index.html").write_text(page(name, SHOTS[name], texts, tag, a.lang), encoding="utf-8")
        print(d / "index.html")
        if a.render:
            raw = d / "renders" / f"{name}{suffix}.mp4"
            subprocess.run(f'npx --yes hyperframes@0.9.65 render -o "{raw}"', cwd=d, shell=True, check=True)
            out = DOCS / f"{name}{suffix}.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-c:v", "libx264", "-crf", "26",
                            "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(out)],
                           check=True)
            print(out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
