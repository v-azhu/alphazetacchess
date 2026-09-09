from alphazetacchess.protocol.search_limits import SearchLimits


def test_movetime_uses_exact_budget():
    limits = SearchLimits(movetime_ms=1500)

    assert limits.time_budget_ms() == 1500


def test_clock_budget_uses_default_twenty_move_allocation():
    limits = SearchLimits(time_ms=10000)

    # 10000 / 20 * 0.8 = 400 ms.
    assert limits.time_budget_ms() == 400


def test_clock_budget_uses_movestogo_when_supplied():
    limits = SearchLimits(time_ms=10000, movestogo=10)

    # 10000 / 10 * 0.8 = 800 ms.
    assert limits.time_budget_ms() == 800


def test_increment_contributes_only_five_percent():
    limits = SearchLimits(time_ms=10000, movestogo=10, increment_ms=1000)

    # 800 ms base allocation + 50 ms increment contribution.
    assert limits.time_budget_ms() == 850


def test_clock_budget_is_capped_at_eighty_percent_of_remaining_time():
    limits = SearchLimits(time_ms=1000, movestogo=1, increment_ms=100000)

    assert limits.time_budget_ms() == 800


def test_clock_budget_never_returns_zero_for_positive_clock():
    limits = SearchLimits(time_ms=1, movestogo=100)

    assert limits.time_budget_ms() == 1


def test_zero_movestogo_is_rejected():
    try:
        SearchLimits(time_ms=1000, movestogo=0)
    except ValueError as exc:
        assert "movestogo" in str(exc)
    else:
        raise AssertionError("movestogo=0 must be rejected")
