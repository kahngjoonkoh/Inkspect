from app.fq import articulation, load_table, lookup

from .conftest import needs_fq_table


@needs_fq_table
def test_table_loads_and_skips_cross_references():
    table = load_table()
    assert len(table) > 5000
    assert all(e.fq in ("o", "u", "-") for e in table)


@needs_fq_table
def test_exact_location_match_gives_fq():
    m = lookup(1, "W", "^", "a bat, the wings spread out")
    assert (m.item, m.content, m.fq, m.location_match) == ("Bat", "A", "o", True)
    assert lookup(1, "W", "^", "an abacus").fq == "-"


@needs_fq_table
def test_plural_and_synonym_forms_match():
    assert lookup(1, "W", "^", "two butterflies").item == "Butterfly"
    m = lookup(2, "D1", "^", "a couple of bears")
    assert m.item == "Bear" and m.fq == "o"


@needs_fq_table
def test_same_object_at_another_location_only_hints_content():
    m = lookup(1, "D2", "^", "a butterfly")
    assert m is not None and m.content == "A" and m.location_match is False


@needs_fq_table
def test_same_object_at_a_listed_other_location_prefers_it():
    m = lookup(1, "D2", "^", "a bat")
    assert m.loc == "D2" and m.fq == "-" and m.location_match


@needs_fq_table
def test_qualifier_breaks_ties():
    m = lookup(1, "W", "^", "an airplane", "seen from the front view")
    assert m.item == "Airplane (Front view)"


@needs_fq_table
def test_unknown_object_returns_none():
    assert lookup(1, "W", "^", "a zzyzx") is None


def test_articulation_counts_parts():
    assert articulation("the head, the wings, the legs and the tail") == 4
    assert articulation("just a shape") == 0


@needs_fq_table
def test_parts_named_only_in_the_inquiry_are_not_the_object():
    m = lookup(7, "D1", "^", "Two girls looking at each other", "here is the head and body")
    assert m is not None and m.content == "H"
    totem = lookup(6, "D1", "^", "A totem pole", "here is the head and body")
    assert totem is None or totem.item.lower().startswith("totem")
