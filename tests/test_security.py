from learning_helper.security import hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    encoded = hash_password("segredo-do-adulto")

    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("segredo-do-adulto", encoded) is True
    assert verify_password("segredo-errado", encoded) is False


def test_password_hashes_use_different_salts() -> None:
    first = hash_password("mesma-senha")
    second = hash_password("mesma-senha")

    assert first != second
    assert verify_password("mesma-senha", first) is True
    assert verify_password("mesma-senha", second) is True


def test_verify_password_rejects_invalid_hashes() -> None:
    for encoded in (
        "",
        "texto",
        "pbkdf2_sha256$abc$00$00",
        "pbkdf2_sha256$1000$zz$00",
        "outro$1000$00$00",
    ):
        assert verify_password("senha", encoded) is False


def test_verify_password_rejects_absurd_iterations() -> None:
    encoded = (
        "pbkdf2_sha256$999999999$"
        "00112233445566778899aabbccddeeff$"
        "00112233445566778899aabbccddeeff"
    )

    assert verify_password("senha", encoded) is False
