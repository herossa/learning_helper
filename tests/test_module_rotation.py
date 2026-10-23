import random
from collections import Counter

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.config import MODULE_ORDER
from learning_helper.persistence.db import Store
from learning_helper.settings import Settings


def _unlock_all(engine: AdaptiveEngine) -> None:
    profile = engine.profile()
    profile.unlocked_modules = list(MODULE_ORDER)
    engine.store.save_profile(profile)


def test_complete_rounds_give_each_module_the_same_count(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(7))
    _unlock_all(engine)

    picks = [engine.pick_module() for _ in range(len(MODULE_ORDER) * 3)]

    assert Counter(picks) == {module: 3 for module in MODULE_ORDER}


def test_each_round_is_a_permutation_of_available_modules(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(11))
    _unlock_all(engine)

    picks = [engine.pick_module() for _ in range(len(MODULE_ORDER) * 2)]

    for start in range(0, len(picks), len(MODULE_ORDER)):
        round_picks = picks[start : start + len(MODULE_ORDER)]
        assert Counter(round_picks) == {module: 1 for module in MODULE_ORDER}


def test_partial_round_counts_differ_by_at_most_one(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(13))
    _unlock_all(engine)

    picks = [engine.pick_module() for _ in range(len(MODULE_ORDER) * 2 + 3)]

    counts = Counter(picks)
    assert set(counts) == set(MODULE_ORDER)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_does_not_repeat_module_between_rounds(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(17))
    _unlock_all(engine)

    picks = [engine.pick_module() for _ in range(100)]

    assert all(previous != current for previous, current in zip(picks, picks[1:]))


def test_new_module_enters_the_current_round_without_duplicates(
    store: Store,
) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(19))
    profile = engine.profile()
    profile.unlocked_modules = ["colors"]
    engine.store.save_profile(profile)

    assert engine.pick_module() == "colors"

    profile = engine.profile()
    profile.unlocked_modules = ["colors", "not_colors"]
    engine.store.save_profile(profile)

    # A rodada atual já teve "colors"; falta apenas o módulo recém-liberado.
    assert engine.pick_module() == "not_colors"

    following = [engine.pick_module() for _ in range(2)]
    assert Counter(following) == {"colors": 1, "not_colors": 1}


def test_only_unlocked_and_enabled_modules_are_picked(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(23))
    engine.store.save_settings(
        Settings(enabled_modules=("colors", "problems"))
    )
    _unlock_all(engine)

    picks = [engine.pick_module() for _ in range(10)]

    assert set(picks) == {"colors", "problems"}


def test_single_available_module_is_always_picked(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(29))

    assert [engine.pick_module() for _ in range(5)] == ["colors"] * 5
