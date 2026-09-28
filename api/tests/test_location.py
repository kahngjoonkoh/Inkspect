import json

import pytest

from app.config import settings
from app.location import map_location, mentions_space, parse_label

from .conftest import square


def test_whole_card_toggle_is_W(toy_map):
    assert map_location(toy_map, [], whole_card=True)["label"] == "W"


def test_loose_lasso_around_all_ink_is_W(toy_map):
    loc = map_location(toy_map, [square(0.05, 0.1, 0.95, 0.9)], False)
    assert loc["code"] == "W" and loc["label"] == "W" and loc["placeholder"] is True


def test_one_side_of_a_mirrored_pair_matches_the_pair_area(toy_map):
    assert map_location(toy_map, [square(0.08, 0.18, 0.32, 0.82)], False)["label"] == "D1"


def test_both_sides_of_a_mirrored_pair_match_it_too(toy_map):
    both = [square(0.08, 0.18, 0.32, 0.82), square(0.68, 0.18, 0.92, 0.82)]
    assert map_location(toy_map, both, False)["label"] == "D1"


def test_lasso_spilling_onto_paper_still_matches(toy_map):
    # Around D2 with a generous margin above it (paper, no ink).
    assert map_location(toy_map, [square(0.28, 0.05, 0.72, 0.42)], False)["label"] == "D2"


def test_small_numbered_detail_is_Dd(toy_map):
    loc = map_location(toy_map, [square(0.44, 0.69, 0.56, 0.81)], False)
    assert (loc["code"], loc["number"], loc["label"]) == ("Dd", 21, "Dd21")


def test_unlisted_area_is_Dd99(toy_map):
    # Half of D2 plus half of the hole's surroundings: no area fits well.
    loc = map_location(toy_map, [square(0.3, 0.3, 0.45, 0.75)], False)
    assert loc["label"] == "Dd99"


def test_selection_off_the_ink_is_Dd99(toy_map):
    assert map_location(toy_map, [square(0.0, 0.85, 0.1, 1.0)], False)["label"] == "Dd99"
    assert map_location(toy_map, [], False)["label"] == "Dd99"


def test_selecting_the_white_space_itself(toy_map):
    loc = map_location(toy_map, [square(0.41, 0.46, 0.59, 0.64)], False)
    assert loc["label"] == "DdS50" and loc["space"] and loc["space_only"]


def test_space_is_coded_only_when_the_response_uses_it(toy_map):
    lasso = [square(0.05, 0.1, 0.95, 0.9)]
    assert map_location(toy_map, lasso, False, uses_space=False)["label"] == "W"
    assert map_location(toy_map, lasso, False, uses_space=True)["label"] == "WS"
    assert mentions_space("a face, the white part is the eyes")
    assert not mentions_space("a bat flying")


@pytest.mark.parametrize("card", range(1, 11))
def test_every_placeholder_area_maps_to_itself(card):
    region_map = json.loads((settings.regions_dir / f"card_{card}.json").read_text())
    assert region_map["placeholder"] is True
    for region in region_map["regions"]:
        if region["kind"] in ("D", "Dd"):
            loc = map_location(region_map, [region["polygons"][0]], False)
            assert loc["label"] in (region["id"], "Dd99"), (card, region["id"], loc)
    d_regions = [r for r in region_map["regions"] if r["kind"] == "D"]
    hits = sum(map_location(region_map, [r["polygons"][0]], False)["label"] == r["id"] for r in d_regions)
    assert hits >= 0.8 * len(d_regions)


def test_parse_label():
    assert parse_label("DdS29") | {} == {"code": "Dd", "number": 29, "space": True, "label": "DdS29",
                                          "placeholder": False, "match": 1.0, "space_only": False}
    assert parse_label("W")["label"] == "W"
    with pytest.raises(ValueError):
        parse_label("X1")
