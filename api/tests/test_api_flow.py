from app import examiner as ex


def start(client):
    r = client.post("/api/sessions", json={"consent": True})
    assert r.status_code == 200
    return r.json()["id"]


def add(client, sid, card, text, orientation="^"):
    return client.post(f"/api/sessions/{sid}/responses",
                       json={"card": card, "verbatim": text, "orientation": orientation, "reaction_ms": 1200}).json()


def nxt(client, sid, card):
    return client.post(f"/api/sessions/{sid}/cards/{card}/next", json={}).json()


def run_response_phase(client, sid, per_card=2):
    for card in range(1, 11):
        for i in range(per_card):
            assert add(client, sid, card, f"a flying bat number {i}" if card == 1 else f"two dead animals {i}")[
                "accepted"]
        out = nxt(client, sid, card)
        if out["action"] == "stay":  # the one-time Card I prompt
            out = nxt(client, sid, card)
    return out


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "db": "ok", "scorer": "ok"}


def test_consent_is_required(client):
    assert client.post("/api/sessions", json={"consent": False}).status_code == 400


def test_examiner_rules_through_the_api(client):
    sid = start(client)
    rejected = add(client, sid, 1, "an inkblot")
    assert not rejected["accepted"] and rejected["message"] == ex.INKBLOT_MESSAGE
    assert client.post(f"/api/sessions/{sid}/responses", json={"card": 2, "verbatim": "x"}).status_code == 409

    empty = nxt(client, sid, 1)
    assert empty["action"] == "stay" and empty["message"] == ex.EMPTY_CARD_MESSAGE
    assert add(client, sid, 1, "a bat")["accepted"]
    single = nxt(client, sid, 1)
    assert single["action"] == "stay" and single["message"] == ex.CARD1_SINGLE_MESSAGE
    assert nxt(client, sid, 1)["action"] == "next_card"

    for i in range(4):
        out = add(client, sid, 2, f"thing {i}")
    fifth = add(client, sid, 2, "thing 4")
    assert fifth["accepted"] and fifth["card_full"]
    assert not add(client, sid, 2, "thing 5")["accepted"]


def test_delete_response_on_current_card(client):
    sid = start(client)
    rid = add(client, sid, 1, "a bat")["response"]["id"]
    state = client.delete(f"/api/sessions/{sid}/responses/{rid}").json()
    assert state["total_responses"] == 0


def test_short_record_is_readministered(client):
    sid = start(client)
    out = run_response_phase(client, sid, per_card=1)
    assert out["action"] == "readminister" and out["message"] == ex.READMINISTER_MESSAGE
    state = out["state"]
    assert state["administration"] == 2 and state["current_card"] == 1 and state["total_responses"] == 0
    out = run_response_phase(client, sid, per_card=1)
    assert out["action"] == "inquiry"  # only once


def test_full_session_to_results(client, scorer, admin):
    sid = start(client)
    out = run_response_phase(client, sid, per_card=2)
    assert out["action"] == "inquiry"
    state = client.get(f"/api/sessions/{sid}").json()
    assert state["phase"] == "inquiry" and state["total_responses"] == 20

    for i, resp in enumerate(state["responses"]):
        rid = resp["id"]
        # Not done yet -> finishing is refused.
        if i == 0:
            assert client.post(f"/api/sessions/{sid}/finish").status_code == 409
            assert client.post(f"/api/responses/{rid}/inquiry/done").status_code == 400
        body = {"regions": [] if i % 2 else [[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]],
                "whole_card": bool(i % 2), "explanation": "the wings are pretty" if i == 0 else "the shape"}
        saved = client.put(f"/api/responses/{rid}/inquiry", json=body).json()
        if i == 0:
            assert saved["followup"].startswith("You said")
            again = client.post(f"/api/responses/{rid}/followups",
                                json={"prompt": saved["followup"], "answer": "the colours"}).json()
            assert again["followup"] is None and again["response"]["inquiry"]["followups"][0]["answer"] == "the colours"
        else:
            assert saved["followup"] is None
        assert client.post(f"/api/responses/{rid}/inquiry/done").status_code == 200

    res = client.post(f"/api/sessions/{sid}/finish").json()
    assert len(scorer.code_calls) == 20
    first = scorer.code_calls[0]
    assert first["location"]["label"] == "W" and first["fq_hint"]["item"] == "Bat"
    assert res["valid"] and len(res["protocol"]) == 20
    assert res["protocol"][0]["score_line"].startswith("Wo FMa o A P 1.0")
    assert any("placeholder" in w for w in res["warnings"])
    assert {s["title"] for s in res["summary"]["sections"]} >= {"Core", "Affect", "Mediation"}
    assert len(res["summary"]["constellations"]) == 6 and res["interpretation"]["clusters"]
    assert client.get(f"/api/sessions/{sid}/results").json() == res

    # Reviewer override -> recomputed summary + training export.
    assert client.get("/api/admin/sessions").status_code == 401
    listed = client.get("/api/admin/sessions", headers=admin).json()
    assert listed[0]["id"] == sid
    rid = res["protocol"][0]["response_id"]
    changed = client.put(f"/api/admin/responses/{rid}/codes", headers=admin,
                         json={"location_label": "D4", "determinants": ["Ma"], "contents": ["H"], "fq": "u"}).json()
    row = changed["protocol"][0]
    assert row["overridden"] and row["location"]["label"] == "D4" and row["score_line"].startswith("Do 4 Ma u H")
    assert row["raw_codes"]["determinants"] == ["FMa"]
    assert client.put(f"/api/admin/responses/{rid}/codes", headers=admin,
                      json={"location_label": "Q9"}).status_code == 400
    export = client.get("/api/admin/export/training.jsonl", headers=admin).text.strip().splitlines()
    assert len(export) == 1 and '"source": "override"' in export[0] and '"Ma"' in export[0]
    reverted = client.delete(f"/api/admin/responses/{rid}/codes", headers=admin).json()
    assert not reverted["protocol"][0]["overridden"]


def test_region_maps_public_read_admin_write(client, admin, toy_map):
    assert client.get("/api/regions/3").json()["placeholder"] is True
    assert client.put("/api/admin/regions/1", json=toy_map).status_code == 401
    saved = client.put("/api/admin/regions/1", json=toy_map | {"placeholder": False}, headers=admin)
    assert saved.status_code == 200 and client.get("/api/regions/1").json()["placeholder"] is False
    no_w = toy_map | {"regions": toy_map["regions"][1:]}
    assert client.put("/api/admin/regions/1", json=no_w, headers=admin).status_code == 400
    assert len(client.get("/api/cards").json()) == 10
