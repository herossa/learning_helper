from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import ACCURACY_WINDOW, MODULE_ORDER


def _spec(module_id: str) -> ChallengeSpec:
    return ChallengeSpec(
        module_id=module_id,
        level=1,
        prompt="p",
        choices=(ChallengeChoice(id="ok", label="ok"), ChallengeChoice(id="no", label="no")),
        correct_id="ok",
    )


def test_unlocked_module_never_removed(engine: AdaptiveEngine) -> None:
    for _ in range(ACCURACY_WINDOW):
        engine.record_attempt(_spec("colors"), "ok")
    assert "not_colors" in engine.profile().unlocked_modules
    for _ in range(ACCURACY_WINDOW):
        engine.record_attempt(_spec("not_colors"), "no")
    unlocked = engine.profile().unlocked_modules
    assert "not_colors" in unlocked
    assert unlocked[0] == MODULE_ORDER[0]
