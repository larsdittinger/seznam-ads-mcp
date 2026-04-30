from sklik_mcp.core.formatting import add_kc_field, format_money_haler, format_pct, parse_date


def test_format_money_haler_to_kc():
    # Sklik returns money in haléře (1 Kč = 100 haléřů)
    assert format_money_haler(12345) == "123.45 Kč"
    assert format_money_haler(0) == "0.00 Kč"
    assert format_money_haler(100) == "1.00 Kč"


def test_format_pct():
    assert format_pct(0.1234) == "12.34%"
    assert format_pct(0) == "0.00%"


def test_parse_date_iso():
    d = parse_date("2026-04-30")
    assert d.year == 2026
    assert d.month == 4
    assert d.day == 30


def test_add_kc_field_default_spend():
    out = add_kc_field({"spend": 12345, "clicks": 5})
    assert out["spend_kc"] == 123.45
    # Original key preserved
    assert out["spend"] == 12345
    assert out["clicks"] == 5


def test_add_kc_field_custom_source():
    out = add_kc_field({"value": 250}, source="value")
    assert out["value_kc"] == 2.5


def test_add_kc_field_missing_source_is_noop():
    out = add_kc_field({"clicks": 5})
    assert "spend_kc" not in out
    assert out == {"clicks": 5}


def test_add_kc_field_returns_copy():
    src = {"spend": 100}
    add_kc_field(src)
    assert "spend_kc" not in src  # input untouched
