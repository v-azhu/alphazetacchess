from web import server


def test_web_api_can_start_depth_six_search_configuration():
    client = server.app.test_client()

    try:
        response = client.post("/api/new_game", json={"ai_depth": 6})

        assert response.status_code == 200
        assert response.get_json()["ai_depth"] == 6
        assert server.game["ai_engine"].depth == 6
        assert server.game["ai_engine"].use_late_move_reductions is True
    finally:
        server.new_game(ai_depth=5)


def test_web_late_move_reductions_default_on_and_can_be_disabled():
    assert server.game["eval_flags"]["use_late_move_reductions"] is True
    assert server.game["ai_engine"].use_late_move_reductions is True

    server.new_game(eval_flags={"use_late_move_reductions": False})

    assert server.game["eval_flags"]["use_late_move_reductions"] is False
    assert server.game["ai_engine"].use_late_move_reductions is False

    server.new_game()


def test_web_quiescence_see_ordering_defaults_on_and_can_be_disabled():
    assert server.game["eval_flags"]["use_see_quiescence_ordering"] is False
    assert server.game["ai_engine"].use_see_quiescence_ordering is False

    server.new_game(eval_flags={"use_see_quiescence_ordering": True})

    assert server.game["eval_flags"]["use_see_quiescence_ordering"] is True
    assert server.game["ai_engine"].use_see_quiescence_ordering is True

    server.new_game()
