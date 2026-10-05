from licitacoes.services.money import format_brl, format_plain, parse_brl_to_cents


def test_parse_formatos_brasileiros():
    assert parse_brl_to_cents("31,51") == 3151
    assert parse_brl_to_cents("R$ 1.234,56") == 123456
    assert parse_brl_to_cents("R\\$ 26.752,96") == 2675296      # como vem no .md
    assert parse_brl_to_cents("11") == 1100
    assert parse_brl_to_cents("8,5") == 850
    assert parse_brl_to_cents("31.51") == 3151                  # estilo inglês com 2 casas


def test_parse_invalidos():
    for bad in ("", None, "abc", "1,2,3", "-5,00", "8,50x"):
        assert parse_brl_to_cents(bad) is None


def test_sem_erro_de_float():
    assert parse_brl_to_cents("0,10") + parse_brl_to_cents("0,20") == 30


def test_format():
    assert format_brl(2675296) == "R$ 26.752,96"
    assert format_brl(5) == "R$ 0,05"
    assert format_plain(3151) == "31,51"
