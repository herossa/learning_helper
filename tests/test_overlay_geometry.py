from learning_helper.overlay.geometry import format_geometry


def test_primary_monitor_at_origin() -> None:
    assert format_geometry(1920, 1080) == "1920x1080+0+0"


def test_monitor_to_the_left_uses_negative_x() -> None:
    assert format_geometry(1920, 1080, -1920, 0) == "1920x1080-1920+0"


def test_monitor_above_uses_negative_y() -> None:
    assert format_geometry(1920, 1080, 0, -1080) == "1920x1080+0-1080"


def test_monitor_to_the_right_uses_positive_x() -> None:
    assert format_geometry(1366, 768, 1920, 0) == "1366x768+1920+0"
