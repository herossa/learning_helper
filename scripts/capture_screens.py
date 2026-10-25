"""Gera as capturas de tela usadas na documentação.

As telas Tk são montadas diretamente com os mesmos componentes do app, em um
banco temporário e com dados de demonstração. O painel de estatísticas usa um
navegador automatizado (Selenium + Firefox/geckodriver).

Uso:
    uv run --with selenium python scripts/capture_screens.py
    uv run python scripts/capture_screens.py --only desafios,configuracoes
"""

from __future__ import annotations

import argparse
import gc
import os
import random
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image, ImageGrab  # noqa: E402

import customtkinter  # noqa: E402

from learning_helper.challenges.registry import build_challenge  # noqa: E402
from learning_helper.config import MODULE_LABELS, MODULE_ORDER  # noqa: E402
from learning_helper.overlay.bathroom import BathroomPanel  # noqa: E402
from learning_helper.overlay.host import ChallengePanel  # noqa: E402
from learning_helper.overlay.main_window import (  # noqa: E402
    PANEL_RELHEIGHT,
    PANEL_RELWIDTH,
)
from learning_helper.overlay.settings_window import SettingsWindow  # noqa: E402
from learning_helper.persistence.db import Store  # noqa: E402
from learning_helper.stats.launcher import build_window as build_stats_window  # noqa: E402

OVERLAY_WIDTH = 1280
OVERLAY_HEIGHT = 720
SETTINGS_GEOMETRY = "820x780+80+60"
SCREENSHOT_DELAY = 0.35

CHALLENGE_LEVELS = {
    "colors": 1,
    "not_colors": 2,
    "compare": 2,
    "math": 2,
    "problems": 2,
    "questions": 1,
    "reading": 1,
}

GROUPS = (
    "desafios",
    "feedback",
    "lembrete",
    "configuracoes",
    "estatisticas",
    "launcher",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "screenshots",
        help="pasta de saída (padrão: docs/screenshots)",
    )
    parser.add_argument(
        "--only",
        default="",
        help="lista separada por vírgula: " + ", ".join(GROUPS),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="semente dos desafios (padrão: 42)",
    )
    return parser.parse_args()


def _selected(only: str) -> set[str]:
    if not only:
        return set(GROUPS)
    selected = {item.strip() for item in only.split(",") if item.strip()}
    unknown = selected - set(GROUPS)
    if unknown:
        raise SystemExit(
            f"Grupo desconhecido: {', '.join(sorted(unknown))}. "
            f"Use: {', '.join(GROUPS)}"
        )
    return selected


def _panel_window() -> customtkinter.CTk:
    customtkinter.set_appearance_mode("light")
    root = customtkinter.CTk()
    root.overrideredirect(True)
    root.geometry(f"{OVERLAY_WIDTH}x{OVERLAY_HEIGHT}+0+0")
    root.configure(fg_color="#000000")
    return root


def _bring_to_front(root) -> None:
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    root.lift()
    try:
        root.focus_force()
    except Exception:
        pass


def _capture(root, path: Path) -> None:
    """Captura a área cliente da janela em ``path``."""
    _bring_to_front(root)
    root.update_idletasks()
    root.update()
    time.sleep(SCREENSHOT_DELAY)
    root.update()

    x = root.winfo_rootx()
    y = root.winfo_rooty()
    width = root.winfo_width()
    height = root.winfo_height()
    if width < 2 or height < 2:
        raise RuntimeError(f"Janela sem área visível: {width}x{height}")

    try:
        image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    except Exception:
        _capture_with_xwd(root, path)
        with Image.open(path) as captured:
            captured.convert("RGB").save(path, optimize=True)
        return
    image.convert("RGB").save(path, optimize=True)


def _capture_with_xwd(root, path: Path) -> None:
    """Fallback para X11 quando o Pillow não consegue capturar a tela."""
    xwd = path.with_suffix(".xwd")
    try:
        subprocess.run(
            [
                "xwd",
                "-silent",
                "-id",
                f"0x{root.winfo_id():x}",
                "-out",
                str(xwd),
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(xwd),
                str(path),
            ],
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Não foi possível capturar a tela. Rode em uma sessão gráfica "
            "X11 (ou instale xwd e ffmpeg)."
        ) from exc
    finally:
        xwd.unlink(missing_ok=True)


def _destroy(root) -> None:
    # O customtkinter agenda checagens periódicas; cancelar antes de destruir
    # evita mensagens de "invalid command name" no terminal.
    try:
        for job in root.tk.call("after", "info"):
            try:
                root.after_cancel(job)
            except Exception:
                pass
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
    # O próximo CTk precisa virar o root padrão para que o ImageTk crie as
    # imagens no interpretador Tcl certo.
    try:
        import tkinter

        if tkinter._default_root is root:
            tkinter._default_root = None
    except Exception:
        pass
    gc.collect()


def capture_challenges(out: Path, seed: int) -> None:
    for index, module in enumerate(MODULE_ORDER, start=1):
        spec = build_challenge(
            module,
            CHALLENGE_LEVELS[module],
            random.Random(seed + index),
        )
        root = _panel_window()
        panel = ChallengePanel(
            root,
            spec,
            on_answer=lambda *_args: None,
            feedback_ms=60_000,
            answer_delay_ms=0,
        )
        panel.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=PANEL_RELWIDTH,
            relheight=PANEL_RELHEIGHT,
        )
        _capture(root, out / f"{index:02d}-desafio-{_slug(MODULE_LABELS[module])}.png")
        _destroy(root)


def capture_feedback(out: Path, seed: int) -> None:
    for name, correct in (("certo", True), ("errado", False)):
        spec = build_challenge("math", 2, random.Random(seed + 100))
        root = _panel_window()
        panel = ChallengePanel(
            root,
            spec,
            on_answer=lambda *_args: None,
            feedback_ms=60_000,
            answer_delay_ms=0,
        )
        panel.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=PANEL_RELWIDTH,
            relheight=PANEL_RELHEIGHT,
        )
        root.update()
        choice = spec.correct_id if correct else _wrong_choice(spec)
        panel._choose(choice)
        _capture(root, out / f"{8 if correct else 9:02d}-feedback-{name}.png")
        _destroy(root)


def capture_bathroom(out: Path) -> None:
    root = _panel_window()
    panel = BathroomPanel(root, seconds=60, on_finished=lambda: None)
    panel.place(
        relx=0.5,
        rely=0.5,
        anchor="center",
        relwidth=PANEL_RELWIDTH,
        relheight=PANEL_RELHEIGHT,
    )
    _capture(root, out / "10-lembrete-banheiro.png")
    _destroy(root)


def capture_settings(out: Path, db_path: Path) -> None:
    store = Store(db_path)
    try:
        # Caminho apenas ilustrativo: não grava nada na pasta real do usuário.
        if sys.platform == "win32":
            display_db = Path(
                r"C:\Users\usuario\AppData\Local\learning_helper\learning_helper.db"
            )
        else:
            display_db = Path(
                "/home/usuario/.local/share/learning_helper/learning_helper.db"
            )
        store.db_path = display_db

        first = SettingsWindow(store, first_run=True)
        first.geometry(SETTINGS_GEOMETRY)
        first.update()
        _capture(first, out / "11-configuracao-inicial-topo.png")
        _scroll_to(first, 1.0)
        _capture(first, out / "12-configuracao-inicial-fim.png")
        _destroy(first)

        store.complete_onboarding()
        normal = SettingsWindow(store, first_run=False)
        normal.geometry(SETTINGS_GEOMETRY)
        normal.update()
        for number, fraction, name in (
            (13, 0.0, "topo"),
            (14, 0.3, "meio"),
            (15, 1.0, "fim"),
        ):
            _scroll_to(normal, fraction)
            _capture(normal, out / f"{number}-configuracoes-{name}.png")
        _destroy(normal)
    finally:
        store.close()


def _scroll_to(window, fraction: float) -> None:
    scrollable = _find_scrollable(window)
    if scrollable is None:
        return
    scrollable._parent_canvas.yview_moveto(fraction)
    window.update_idletasks()
    window.update()


def _find_scrollable(widget):
    for child in widget.winfo_children():
        if isinstance(child, customtkinter.CTkScrollableFrame):
            return child
        found = _find_scrollable(child)
        if found is not None:
            return found
    return None


def capture_launcher(out: Path) -> None:
    root = build_stats_window(
        "http://127.0.0.1:8501",
        on_close=lambda window: window.destroy(),
    )
    root.geometry("540x210+120+120")
    _capture(root, out / "19-janela-estatisticas.png")
    _destroy(root)


def _wrong_choice(spec) -> str:
    accepted = set(spec.accepted_ids())
    for choice in spec.choices:
        if choice.id not in accepted:
            return choice.id
    return spec.correct_id


def _seed_stats_db(db_path: Path) -> None:
    store = Store(db_path)
    profile = store.get_profile()
    profile.unlocked_modules = list(MODULE_ORDER)
    profile.levels = {
        module: 1 + ((index * 2) % 5) for index, module in enumerate(MODULE_ORDER)
    }
    store.save_profile(profile)
    store.complete_onboarding()

    now = datetime.now(timezone.utc)
    for days_ago in range(10, -1, -1):
        for attempt in range(4):
            module = MODULE_ORDER[(days_ago + attempt) % len(MODULE_ORDER)]
            level = profile.levels[module]
            spec = build_challenge(
                module,
                level,
                random.Random(days_ago * 100 + attempt),
            )
            correct = (days_ago + attempt) % 5 != 0
            given = _given_answer(spec, correct)
            store.insert_attempt(
                module_id=module,
                level=level,
                prompt=spec.prompt,
                choices=[choice.label for choice in spec.choices],
                correct_answer=spec.answer_text,
                given_answer=given,
                is_correct=correct,
                created_at=now - timedelta(days=days_ago, hours=attempt),
            )
    store.close()


def _given_answer(spec, correct: bool) -> str:
    if correct:
        return _choice_label(spec, spec.correct_id)
    if spec.input_mode == "text":
        try:
            return str(int(spec.correct_id) + 1)
        except ValueError:
            return "0"
    return _choice_label(spec, _wrong_choice(spec))


def _choice_label(spec, choice_id: str) -> str:
    for choice in spec.choices:
        if choice.id == choice_id:
            return choice.label
    return choice_id


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(port: int, process: subprocess.Popen, timeout: float = 40) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("O servidor de estatísticas encerrou antes de ficar pronto.")
        try:
            with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                if 200 <= response.status < 300:
                    return
        except (URLError, OSError):
            pass
        time.sleep(0.3)
    raise RuntimeError("Tempo esgotado esperando o servidor de estatísticas.")


def capture_stats(out: Path, temp_dir: Path) -> None:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:
        raise RuntimeError(
            "Selenium não está instalado. Rode com "
            "`uv run --with selenium python scripts/capture_screens.py`."
        ) from exc

    db_path = temp_dir / "learning_helper.db"
    _seed_stats_db(db_path)
    port = _free_port()
    command = [
        sys.executable,
        "-m",
        "learning_helper",
        "--stats-server",
        "--stats-port",
        str(port),
        "--db",
        str(db_path),
    ]
    log_path = temp_dir / "stats-server.log"
    environment = os.environ.copy()
    environment["STREAMLIT_CLIENT_TOOLBAR_MODE"] = "minimal"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=environment,
        )
        try:
            _wait_for_server(port, process)
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            options.set_preference("intl.accept_languages", "pt-BR,pt")
            options.set_preference("intl.locale.requested", "pt-BR")
            snap_firefox = Path("/snap/firefox/current/usr/lib/firefox/firefox")
            if snap_firefox.is_file():
                # O wrapper /usr/bin/firefox do snap não é reconhecido pelo
                # geckodriver como executável do Firefox.
                options.binary_location = str(snap_firefox)
            driver = webdriver.Firefox(options=options)
            try:
                driver.set_window_size(1600, 1200)
                driver.get(f"http://127.0.0.1:{port}")
                WebDriverWait(driver, 40).until(
                    lambda current: current.find_elements(
                        By.CSS_SELECTOR, '[data-testid="stMetric"]'
                    )
                )
                time.sleep(1.0)
                _capture_tabs(driver, By, out, WebDriverWait)
            finally:
                driver.quit()
        except Exception:
            if log_path.exists():
                print(log_path.read_text(encoding="utf-8"), file=sys.stderr)
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def _capture_tabs(driver, By, out: Path, WebDriverWait) -> None:
    tabs = {
        "Evolução": "16-estatisticas-evolucao.png",
        "Módulos e níveis": "17-estatisticas-modulos.png",
        "Tentativas recentes": "18-estatisticas-tentativas.png",
    }
    driver.execute_script(
        """
        document.querySelectorAll('p').forEach((item) => {
            if (item.textContent.trim().startsWith('Banco:')) {
                item.textContent = 'Banco: dados de demonstração';
            }
        });
        """
    )
    buttons = WebDriverWait(driver, 20).until(
        lambda current: current.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        or False
    )
    by_text = {button.text.strip(): button for button in buttons}
    for label, filename in tabs.items():
        button = by_text.get(label)
        if button is None:
            raise RuntimeError(f"Aba não encontrada: {label}")
        button.click()
        time.sleep(1.0)
        path = out / filename
        driver.save_screenshot(str(path))
        with Image.open(path) as captured:
            captured.convert("RGB").save(path, optimize=True)


def _slug(text: str) -> str:
    replacements = {
        "á": "a",
        "â": "a",
        "ã": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    lowered = text.lower()
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    return "-".join(lowered.split())


def main() -> int:
    args = _parse_args()
    selected = _selected(args.only)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    try:
        import tkinter

        probe = tkinter.Tk()
        probe.withdraw()
        probe.destroy()
        tkinter._default_root = None
    except Exception:
        print(
            "Não foi possível abrir uma janela Tk. Rode em uma sessão gráfica "
            "(DISPLAY configurado).",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="learning-helper-shots-") as raw_temp:
        temp_dir = Path(raw_temp)
        if "desafios" in selected:
            capture_challenges(out, args.seed)
        if "feedback" in selected:
            capture_feedback(out, args.seed)
        if "lembrete" in selected:
            capture_bathroom(out)
        if "configuracoes" in selected:
            capture_settings(out, temp_dir / "settings.db")
        if "estatisticas" in selected:
            try:
                capture_stats(out, temp_dir)
            except RuntimeError as exc:
                print(f"Aviso: {exc}", file=sys.stderr)
        if "launcher" in selected:
            capture_launcher(out)

    print(f"Capturas salvas em {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
