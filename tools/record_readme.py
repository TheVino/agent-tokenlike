"""Generates docs/screenshot.png and docs/demo.gif with the real app (real Tk + Pillow, Windows only).

Uses a temporary HOME and fake data (nothing from the real progress or the user's screen: a dark backdrop
stays behind the transparent pet). Usage: python tools/record_readme.py [gif_seconds] [en|pt]
"""
import os, random, sys, tempfile, time, types
from pathlib import Path

home = tempfile.mkdtemp()
os.environ["HOME"] = home
os.environ["USERPROFILE"] = home
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import tkinter, tkinter.font  # noqa: E401,F401
from PIL import Image, ImageGrab
import dungeon as M
import tokenlike as tp

BACKDROP = "#16131f"
DOCS = REPO_ROOT / "docs"
SEG = float(sys.argv[1]) if len(sys.argv) > 1 else 14
LANG = sys.argv[2] if len(sys.argv) > 2 else "en"           # the README is in English
X0, Y0, W, H = 700, 60, 800, 760          # captured area (backdrop) on screen
PET = (X0 + W - 380, Y0 + H - 360)         # pet corner: on the right (the Profile stays on the left)

tp.tk = tkinter
tp.DATA_DIR = Path(home) / ".tokenlike"
tp.LOG_FILE = tp.DATA_DIR / "tokenlike.log"
app = tp.PetApp(types.SimpleNamespace(demo=True, import_history=False, reset=False))
app.reader.poll = lambda: (0.0, 0)
app.refresh_limits = lambda: None
rng = random.Random(7)

# sample data
m = app.meta
m["achievements"] = ["floor5", "boss1", "mimic", "rich", "poison1", "burn1", "dodge10", "floor10"]
m["runs"], m["best"], m["bosses"] = 23, {"floor": 14, "room": 2}, 4
m["next_char"] = "slime"
app.new_run(announce=False)
keys = list(M.ITEMS)
app.run["items"] = [{"key": k, "rar": rng.choice(M.RARITIES)} for k in rng.sample(keys, 7)]
app.run.update(floor=4, room=2, gold=88, kills=21, stage=1, energy=1.5e6)
now = time.time()
for d in range(8):
    tp.add_usage(app.state, now - d * 86400, 2.5e6 * (8 - d))
app.state.update(tokens_total=60e6, xp_total=48e6, daily={tp.date.today().isoformat(): 4e6})
app.limits = {"session": (38, now + 2 * 3600), "week": (61, now + 3 * 86400), "updated": now}
app.lang_var.set(LANG); app.change_lang()
app.load_images(); app.refresh_look(); app.update_panel()
app.root.geometry(f"+{PET[0]}+{PET[1]}")

# backdrop: its own Tk, created after the app (the 1st Tk owns the images; and a Toplevel of the pet
# would always stay above it on Windows)
backdrop = tkinter.Tk()
backdrop.overrideredirect(True)
backdrop.configure(bg=BACKDROP)
backdrop.geometry(f"{W}x{H}+{X0}+{Y0}")
backdrop.attributes("-topmost", True)


def on_top():
    app.root.attributes("-topmost", True); app.root.lift()


def wait(s):
    end = time.time() + s
    while time.time() < end:
        app.root.update(); backdrop.update(); time.sleep(0.02)


def snapshot():
    """Captures the area; if the border (8 px) is not only the backdrop, something from the user's screen got in (Alt+Tab, notification,
    another window on top): stops without saving anything."""
    img = ImageGrab.grab((X0, Y0, X0 + W, Y0 + H), all_screens=True).convert("RGB")
    color = tuple(int(BACKDROP[i:i + 2], 16) for i in (1, 3, 5))
    for box in ((0, 0, W, 8), (0, H - 8, W, H), (0, 0, 8, H), (W - 8, 0, W, H)):
        colors = img.crop(box).getcolors(1 << 16) or []
        if [c for _, c in colors] != [color]:
            print("border", box, sorted(colors, reverse=True)[:5])
            app.root.destroy()
            sys.exit("the screen changed during the capture (another window on top?); nothing was saved. Run it again without touching the PC.")
    return img


DOCS.mkdir(exist_ok=True)
wait(0.3); on_top(); wait(9)                # skips the welcome bubble and DEMO MODE

# GIF: the pet playing by itself (fake demo tokens)
frames, step = [], 0.1
end = time.time() + SEG
while time.time() < end:
    t0 = time.time()
    wait(0)
    frames.append(snapshot())
    wait(max(0.0, step - (time.time() - t0)))
box = (PET[0] - X0 - 250, PET[1] - Y0 - 120, PET[0] - X0 + app.W + 10, PET[1] - Y0 + app.H + 10)
frames = [q.crop(box) for q in frames]                     # the pet, the panel and the bubbles above
pal = frames[len(frames) // 2].quantize(colors=128, method=Image.MEDIANCUT)
gif = [q.quantize(palette=pal, dither=Image.NONE) for q in frames]
gif[0].save(DOCS / "demo.gif", save_all=True, append_images=gif[1:], duration=int(step * 1000),
            loop=0, optimize=True)
print("docs/demo.gif", len(gif), "quadros", (DOCS / "demo.gif").stat().st_size // 1024, "KB")

# screenshot: pet + Profile open beside it
app.demo = False                    # no "(demo mode)" tag in the footer
app.state.setdefault("windows", {})["profile_win"] = [X0 + 10, Y0 + 20]
app.show_profile()
w = app.profile_win
w.unbind("<FocusOut>")
on_top(); w.attributes("-topmost", True); w.lift(); wait(1.5)
w.geometry(f"+{X0 + 10}+{Y0 + 20}"); wait(0.5)   # the 2nd Tk (backdrop) sometimes sends the window back next to the pet
assert (w.winfo_x(), w.winfo_y()) == (X0 + 10, Y0 + 20), (w.winfo_x(), w.winfo_y())
img = snapshot()
img.save(DOCS / "screenshot.png")
print("docs/screenshot.png", img.size)
app.root.destroy(); backdrop.destroy()
