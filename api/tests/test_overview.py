from app.overview import BANDS, overview
from app.summary import compute

from .test_summary import EXAMPLE, row


def test_example_protocol_bands():
    o = overview(compute(EXAMPLE))
    assert o["available"] and [b["key"] for b in o["bands"]] == [b.key for b in BANDS]
    bands = {b["key"]: b for b in o["bands"]}
    assert bands["responses"]["level"] == "typical" and bands["responses"]["value"] == "18"
    assert bands["big_picture"]["value"] == "44%" and bands["big_picture"]["level"] == "typical"
    assert bands["imagination"]["level"] == "lower"      # M = 1
    assert bands["emotion"]["level"] == "lower"          # WSumC = 0
    assert bands["conventional"]["level"] == "typical"   # P = 5
    assert bands["people"]["level"] == "lower"           # no human content
    assert all(b["text"] and b["typical"] for b in o["bands"])


def test_higher_band():
    rows = [row(3, "D", 9, "+", ["Ma"], "o", ["H"], pair=True, popular=True)] * 16
    bands = {b["key"]: b for b in overview(compute(rows))["bands"]}
    assert bands["imagination"]["level"] == "higher" and bands["people"]["level"] == "higher"
    assert bands["conventional"]["level"] == "higher" and bands["big_picture"]["level"] == "lower"


def test_short_record_has_no_bands():
    o = overview(compute(EXAMPLE[:10]))
    assert not o["available"] and o["bands"] == [] and "14" in o["message"]
