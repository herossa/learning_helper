from __future__ import annotations

import random
from dataclasses import dataclass

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import MAX_LEVEL

OPS = {
    1: ("+", 1, 10),
    2: ("+", 1, 20),
    3: ("-", 1, 20),
    4: ("mix", 1, 40),
    5: ("*", 1, 10),
}

NAMES = ("Ana", "Bruno", "Carla", "Davi", "Elisa", "Felipe", "Gabriela", "Hugo")


@dataclass(frozen=True)
class Item:
    singular: str
    plural: str
    feminine: bool = False

    def describe(self, count: int) -> str:
        noun = self.singular if count == 1 else self.plural
        return f"{count} {noun}"

    @property
    def many(self) -> str:
        return "Quantas" if self.feminine else "Quantos"

    @property
    def com_many(self) -> str:
        return "Com quantas" if self.feminine else "Com quantos"


@dataclass(frozen=True)
class Scenario:
    id: str
    op: str
    template: str


ITEMS = (
    Item("figurinha", "figurinhas", feminine=True),
    Item("lápis", "lápis"),
    Item("bolinha de gude", "bolinhas de gude", feminine=True),
    Item("maçã", "maçãs", feminine=True),
    Item("carrinho", "carrinhos"),
    Item("adesivo", "adesivos"),
    Item("flor", "flores", feminine=True),
    Item("livro", "livros"),
)

SCENARIOS: dict[str, tuple[Scenario, ...]] = {
    "+": (
        Scenario(
            "gain",
            "+",
            "{name} tinha {a_item} e ganhou mais {b_item}. {many} {plural} {name} tem agora?",
        ),
        Scenario(
            "collect",
            "+",
            "{name} juntou {a_item} com {b_item}. {com_many} {plural} {name} ficou?",
        ),
        Scenario(
            "box",
            "+",
            "Havia {a_item} na caixa e {name} colocou mais {b_item}. "
            "{many} {plural} há na caixa agora?",
        ),
        Scenario(
            "gifts",
            "+",
            "{name} ganhou {a_item} de um amigo e {b_item} de outro. "
            "{many} {plural} {name} ganhou?",
        ),
    ),
    "-": (
        Scenario(
            "give",
            "-",
            "{name} tinha {a_item} e deu {b_item} para um amigo. "
            "{com_many} {plural} {name} ficou?",
        ),
        Scenario(
            "store",
            "-",
            "Eram {a_item} na mesa e {name} guardou {b_item}. "
            "{many} {plural} ficaram na mesa?",
        ),
        Scenario(
            "lost",
            "-",
            "{name} levou {a_item} para a escola e perdeu {b_item} no caminho. "
            "{com_many} {plural} {name} chegou em casa?",
        ),
        Scenario(
            "sold",
            "-",
            "A loja tinha {a_item} e vendeu {b_item}. {many} {plural} ainda estão na loja?",
        ),
    ),
    "*": (
        Scenario(
            "boxes",
            "*",
            "{name} tem {a_containers} com {b_item} em cada uma. "
            "{many} {plural} {name} tem?",
        ),
        Scenario(
            "packages",
            "*",
            "Cada caixa tem {b_item}. {name} comprou {a_containers}. "
            "{many} {plural} {name} comprou?",
        ),
        Scenario(
            "organize",
            "*",
            "{name} organizou {b_item} em cada uma de suas {a_containers}. "
            "{many} {plural} {name} organizou?",
        ),
    ),
}


def _pick_op(level: int, rng: random.Random) -> str:
    op, _, _ = OPS.get(level, OPS[MAX_LEVEL])
    if op == "mix":
        return rng.choice(["+", "-"])
    return op


def _operands(op: str, low: int, high: int, rng: random.Random) -> tuple[int, int, int]:
    if op == "-":
        a = rng.randint(low, high)
        b = rng.randint(low, a)
        return a, b, a - b
    if op == "*":
        # Pelo menos 2 caixas: o enunciado fica natural no plural.
        a = rng.randint(max(low, 2), high)
        b = rng.randint(low, high)
        return a, b, a * b
    a = rng.randint(low, high)
    b = rng.randint(low, high)
    return a, b, a + b


def _containers(count: int) -> str:
    return "1 caixa" if count == 1 else f"{count} caixas"


def _distractors(
    a: int, b: int, op: str, result: int, rng: random.Random
) -> list[int]:
    """Erros plausíveis: conta errada por pouco ou operação trocada."""
    candidates: list[int] = [result + 1, result - 1, result + 2, result - 2]
    if op == "+":
        candidates.append(abs(a - b))
        if a * b <= 121:
            candidates.append(a * b)
    elif op == "-":
        candidates.append(a + b)
        if a * b <= 121:
            candidates.append(a * b)
    else:
        candidates.extend([a + b, result - b, result + b])

    rng.shuffle(candidates)
    values = {result}
    for candidate in candidates:
        if len(values) == 4:
            break
        if candidate >= 0 and (candidate != 0 or result == 0):
            values.add(candidate)

    fallback = (-10, -5, -2, -1, 1, 2, 5, 10)
    while len(values) < 4:
        candidate = result + rng.choice(fallback)
        if candidate >= 0 and (candidate != 0 or result == 0):
            values.add(candidate)

    values.remove(result)
    return list(values)


def build_problems_challenge(
    level: int, rng: random.Random | None = None
) -> ChallengeSpec:
    rng = rng or random.Random()
    clamped = max(1, min(level, MAX_LEVEL))
    _, low, high = OPS[clamped]
    op = _pick_op(clamped, rng)
    a, b, result = _operands(op, low, high, rng)

    scenario = rng.choice(SCENARIOS[op])
    item = rng.choice(ITEMS)
    name = rng.choice(NAMES)
    prompt = scenario.template.format(
        name=name,
        a_item=item.describe(a),
        b_item=item.describe(b),
        a_containers=_containers(a),
        plural=item.plural,
        many=item.many,
        com_many=item.com_many,
    )

    option_values = [result, *_distractors(a, b, op, result, rng)]
    rng.shuffle(option_values)
    choices = tuple(
        ChallengeChoice(id=str(value), label=str(value)) for value in option_values
    )
    return ChallengeSpec(
        module_id="problems",
        level=clamped,
        prompt=prompt,
        choices=choices,
        correct_id=str(result),
        metadata={
            "a": a,
            "b": b,
            "op": op,
            "result": result,
            "scenario": scenario.id,
            "item": item.singular,
        },
    )
