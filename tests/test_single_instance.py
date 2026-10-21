import os
import subprocess
import sys
from pathlib import Path

from learning_helper.single_instance import SingleInstance

SRC = Path(__file__).resolve().parents[1] / "src"


def _child(lock_path: Path) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC)
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from learning_helper.single_instance import SingleInstance\n"
        "ok = SingleInstance(Path(sys.argv[1])).acquire()\n"
        "sys.exit(0 if ok else 3)\n"
    )
    return subprocess.run(
        [sys.executable, "-c", code, str(lock_path)],
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )


def test_second_process_cannot_acquire(tmp_path: Path) -> None:
    lock_path = tmp_path / "app.lock"
    first = SingleInstance(lock_path)
    assert first.acquire()

    child = _child(lock_path)
    assert child.returncode == 3, child.stderr

    first.release()
    again = SingleInstance(lock_path)
    assert again.acquire()
    again.release()


def test_acquire_is_idempotent(tmp_path: Path) -> None:
    lock = SingleInstance(tmp_path / "app.lock")
    assert lock.acquire()
    assert lock.acquire()
    lock.release()
