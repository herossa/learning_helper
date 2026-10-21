import os
import time

from learning_helper import lifecycle


def test_request_quit_is_visible_to_multiple_readers(tmp_path) -> None:
    assert not lifecycle.quit_requested(tmp_path)

    path = lifecycle.request_quit(tmp_path)
    assert path.is_file()
    assert lifecycle.quit_requested(tmp_path)
    # O arquivo não é consumido: outro processo também precisa vê-lo.
    assert lifecycle.quit_requested(tmp_path)

    lifecycle.clear_quit_request(tmp_path)
    assert not lifecycle.quit_requested(tmp_path)


def test_stale_quit_request_is_ignored_and_removed(tmp_path) -> None:
    path = lifecycle.request_quit(tmp_path)
    old = time.time() - lifecycle.QUIT_MAX_AGE_SECONDS - 1
    os.utime(path, (old, old))

    assert not lifecycle.quit_requested(tmp_path)
    assert not path.exists()
