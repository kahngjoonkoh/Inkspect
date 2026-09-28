from app import examiner as ex


def test_inkblot_answers_are_rejected_with_the_cs_prompt():
    for text in ["an inkblot", "Just ink.", "it's a blot of ink", "ink blots", "a big black splotch"]:
        d = ex.decide_add(text, [])
        assert not d.accepted and d.message == ex.INKBLOT_MESSAGE, text


def test_real_answers_mentioning_ink_are_accepted():
    assert ex.decide_add("a bat made of ink", []).accepted
    assert ex.decide_add("a butterfly", []).accepted


def test_blank_and_duplicate_answers_are_ignored_silently():
    assert ex.decide_add("   ", []) == ex.AddDecision(False)
    d = ex.decide_add("A  Bat", ["a bat"])
    assert not d.accepted and d.message is None


def test_fifth_response_fills_the_card_and_a_sixth_is_refused():
    four = ["a", "b", "c", "d"]
    fifth = ex.decide_add("e", four)
    assert fifth.accepted and fifth.card_full and fifth.message == ex.CARD_FULL_MESSAGE
    sixth = ex.decide_add("f", four + ["e"])
    assert not sixth.accepted and sixth.card_full


def test_empty_card_gets_one_encouragement_then_moves_on():
    first = ex.decide_next(3, 0, False, empty_prompted=False, total_r=5, administration=1)
    assert first.action == "stay" and first.message == ex.EMPTY_CARD_MESSAGE
    assert ex.decide_next(3, 0, False, empty_prompted=True, total_r=5, administration=1).action == "next_card"


def test_single_response_on_card_one_is_prompted_once():
    d = ex.decide_next(1, 1, card1_prompted=False, empty_prompted=False, total_r=1, administration=1)
    assert d.action == "stay" and d.message == ex.CARD1_SINGLE_MESSAGE
    assert ex.decide_next(1, 1, card1_prompted=True, empty_prompted=False, total_r=1,
                          administration=1).action == "next_card"
    assert ex.decide_next(2, 1, card1_prompted=False, empty_prompted=False, total_r=2,
                          administration=1).action == "next_card"


def test_short_record_is_readministered_once():
    d = ex.decide_next(10, 1, True, False, total_r=13, administration=1)
    assert d.action == "readminister" and d.message == ex.READMINISTER_MESSAGE
    assert ex.decide_next(10, 1, True, False, total_r=13, administration=2).action == "inquiry"
    assert ex.decide_next(10, 1, True, False, total_r=14, administration=1).action == "inquiry"
