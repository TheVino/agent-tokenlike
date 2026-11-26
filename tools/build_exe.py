"""Builds dist/AgentTokenlike-windows.zip (AgentTokenlike.exe without console + statusline.exe in one folder) and,
when Inno Setup 6 is installed, dist/AgentTokenlike-Setup.exe (per-user installer that updates in place).

Python is not needed to run them. PyInstaller and Inno Setup are only needed here (development only):
    python -m pip install pyinstaller
    winget install JRSoftware.InnoSetup
    python tools/build_exe.py [version]        (default: the latest git tag, without the "v")
"""
import os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD, DIST = ROOT / "build", ROOT / "dist"
APP = "AgentTokenlike"
sys.path.insert(0, str(ROOT))
import tokenlike as tp  # noqa: E402
import tray  # noqa: E402

SPEC = f"""
from PyInstaller.utils.hooks import collect_submodules
app = Analysis([r"{ROOT / 'tokenlike.py'}"], pathex=[r"{ROOT}"], hiddenimports=collect_submodules("heroes"))
sl = Analysis([r"{ROOT / 'statusline.py'}"], pathex=[r"{ROOT}"])
app_exe = EXE(PYZ(app.pure), app.scripts, [], exclude_binaries=True, name="{APP}", console=False,
              icon=r"{BUILD / 'icon.ico'}")
sl_exe = EXE(PYZ(sl.pure), sl.scripts, [], exclude_binaries=True, name="statusline", console=True)
COLLECT(app_exe, app.binaries, app.datas, sl_exe, sl.binaries, sl.datas, name="{APP}")
"""

README = """Agent Tokenlike
===============

Run AgentTokenlike.exe. Keep this folder together (the .exe needs the _internal folder next to it).

Windows may say "Windows protected your PC" because the .exe is not signed: click "More info", then "Run anyway".

Optional session/week bars: add this to %USERPROFILE%\\.claude\\settings.json (use the real path to this folder):

  "statusLine": { "type": "command", "command": "\\"C:/path/to/AgentTokenlike/statusline.exe\\"" }

Extra heroes: put their folders in characters\\ (next to the .exe). More at https://github.com/TheVino/agent-tokenlike
"""


def main():
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(DIST, ignore_errors=True)
    BUILD.mkdir()
    (BUILD / "icon.ico").write_bytes(tray.ico(tp.png_bytes(tp.hero_idle("slime"), 256, square=True)[0], 256))
    (BUILD / f"{APP}.spec").write_text(SPEC, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(DIST),
                    "--workpath", str(BUILD / "work"), str(BUILD / f"{APP}.spec")], check=True)
    out = DIST / APP
    shutil.copytree(ROOT / "characters", out / "characters")
    (out / "README.txt").write_text(README, encoding="utf-8")
    shutil.copy(ROOT / "LICENSE", out / "LICENSE.txt")
    zip_path = shutil.make_archive(str(DIST / f"{APP}-windows"), "zip", DIST, APP)
    print(zip_path, Path(zip_path).stat().st_size // 1024, "KB")
    iscc = shutil.which("ISCC") or next((p for p in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
                                                     Path(r"C:/Program Files (x86)/Inno Setup 6/ISCC.exe")) if p.exists()), None)
    if not iscc:
        print("Inno Setup 6 not found: skipped the installer")
        return
    version = sys.argv[1] if len(sys.argv) > 1 else subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"], cwd=ROOT, capture_output=True, text=True).stdout.strip().lstrip("v")
    subprocess.run([str(iscc), "/Q", f"/DAppVersion={version or '0.0.0'}", f"/DRoot={ROOT}", str(ROOT / "tools/installer.iss")],
                   check=True)
    setup = DIST / f"{APP}-Setup.exe"
    print(setup, setup.stat().st_size // 1024, "KB", "version", version)


if __name__ == "__main__":
    main()
