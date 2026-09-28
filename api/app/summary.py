"""Comprehensive System structural summary.

`compute` returns the raw variables; `sections` and `constellations` format
them for display. Determinant sums count every occurrence, including the
determinants inside blends.
"""

import math
from collections import Counter

from .tables import ROMAN, zest

CONTENT_CODES = ["H", "(H)", "Hd", "(Hd)", "Hx", "A", "(A)", "Ad", "(Ad)", "An", "Art", "Ay", "Bl", "Bt",
                 "Cg", "Cl", "Ex", "Fd", "Fi", "Ge", "Hh", "Ls", "Na", "Sc", "Sx", "Xy", "Id"]
DETERMINANT_ORDER = ["M", "FM", "m", "FC", "CF", "C", "Cn", "FC'", "C'F", "C'", "FT", "TF", "T", "FV", "VF", "V",
                     "FY", "YF", "Y", "Fr", "rF", "FD", "F"]
SPECIAL_WEIGHTS = {"DV1": 1, "INC1": 2, "DR1": 3, "FAB1": 4, "ALOG": 5, "CONTAM": 7,
                   "DV2": 2, "INC2": 4, "DR2": 6, "FAB2": 7}
LEVEL2 = {"DV2", "INC2", "DR2", "FAB2"}
CHROMATIC = {"FC", "CF", "C", "Cn"}
SHADING = {"FC'", "C'F", "C'", "FT", "TF", "T", "FV", "VF", "V", "FY", "YF", "Y"}


def split_movement(det: str) -> tuple[str, str | None]:
    """'FMa' -> ('FM', 'a'); 'Ma-p' -> ('M', 'a-p'); 'FC' -> ('FC', None)."""
    for base in ("FM", "M", "m"):
        if det.startswith(base) and det != base + "'":
            rest = det[len(base):]
            if rest in ("a", "p", "a-p", ""):
                return base, rest or None
    return det, None


def ratio(a: float, b: float) -> float | None:
    return a / b if b else None


def compute(rows: list[dict]) -> dict:
    R = len(rows)
    det_counts: Counter[str] = Counter()
    active = passive = ma = mp = 0
    blends = []
    col_shd = 0
    for row in rows:
        dets = row["determinants"]
        bases = []
        for d in dets:
            base, sup = split_movement(d)
            bases.append(base)
            det_counts[base] += 1
            if sup in ("a", "a-p"):
                active += 1
                ma += base == "M"
            if sup in ("p", "a-p"):
                passive += 1
                mp += base == "M"
        if len(dets) > 1:
            blends.append(".".join(dets))
            if set(bases) & (CHROMATIC - {"Cn"}) and set(bases) & SHADING:
                col_shd += 1

    content = Counter(c for row in rows for c in row["contents"])
    specials = Counter(s for row in rows for s in row["special_scores"])
    fq = Counter(row["fq"] for row in rows)
    loc = Counter(row["location"]["code"] for row in rows)
    dq = Counter(row["dq"] for row in rows)
    pure_f = sum(1 for row in rows if row["determinants"] == ["F"])

    zs = [row["z"] for row in rows if row["z"] is not None]
    zf, zsum = len(zs), sum(zs)
    z_est = zest(zf)

    M, FM, m = det_counts["M"], det_counts["FM"], det_counts["m"]
    FC, CF, C, Cn = det_counts["FC"], det_counts["CF"], det_counts["C"], det_counts["Cn"]
    sum_c_ach = det_counts["FC'"] + det_counts["C'F"] + det_counts["C'"]
    sum_t = det_counts["FT"] + det_counts["TF"] + det_counts["T"]
    sum_v = det_counts["FV"] + det_counts["VF"] + det_counts["V"]
    sum_y = det_counts["FY"] + det_counts["YF"] + det_counts["Y"]
    reflections = det_counts["Fr"] + det_counts["rF"]
    wsumc = 0.5 * FC + 1.0 * CF + 1.5 * C
    ea = M + wsumc
    es = FM + m + sum_c_ach + sum_t + sum_v + sum_y
    adj_es = es - max(0, m - 1) - max(0, sum_y - 1)
    lam = ratio(pure_f, R - pure_f) if R - pure_f else math.inf

    def d_score(diff: float) -> int:
        if abs(diff) <= 2.5:
            return 0
        return int(math.copysign(math.ceil((abs(diff) - 2.5) / 2.5), diff))

    # Erlebnistypus style
    if lam > 0.99:
        style = "Avoidant"
    elif ea < 4:
        style = "Not determined (EA < 4)"
    elif abs(M - wsumc) >= (2.0 if ea <= 10 else 2.5):
        style = "Introversive" if M > wsumc else "Extratensive"
    else:
        style = "Ambitent"
    eb_per = None
    if style in ("Introversive", "Extratensive") and min(M, wsumc) > 0:
        eb_per = max(M, wsumc) / min(M, wsumc)

    wd = [row for row in rows if row["location"]["code"] in ("W", "D")]
    good = ("+", "o", "u")
    m_rows = [row for row in rows if any(split_movement(d)[0] == "M" for d in row["determinants"])]
    r_late = sum(1 for row in rows if row["card"] >= 8)
    r_early = R - r_late
    human = content["H"] + content["(H)"] + content["Hd"] + content["(Hd)"]
    sum6 = sum(specials[s] for s in SPECIAL_WEIGHTS)
    lvl2 = sum(specials[s] for s in LEVEL2)
    wsum6 = sum(w * specials[s] for s, w in SPECIAL_WEIGHTS.items())
    pairs = sum(1 for row in rows if row["pair"])

    approach: dict[str, list[str]] = {}
    for row in rows:
        approach.setdefault(ROMAN[row["card"]], []).append(
            row["location"]["code"] + ("S" if row["location"]["space"] else ""))

    return {
        "R": R, "valid": R >= 14,
        "Zf": zf, "ZSum": zsum, "ZEst": z_est, "Zd": (zsum - z_est) if z_est is not None else None,
        "W": loc["W"], "D": loc["D"], "Dd": loc["Dd"], "S": sum(1 for row in rows if row["location"]["space"]),
        "DQ": {k: dq[k] for k in ("+", "o", "v/+", "v")},
        "FQx": {k: fq[k] for k in ("+", "o", "u", "-", "none")},
        "MQual": {k: sum(1 for r in m_rows if r["fq"] == k) for k in ("+", "o", "u", "-", "none")},
        "WDQual": {k: sum(1 for r in wd if r["fq"] == k) for k in ("+", "o", "u", "-", "none")},
        "determinants": {d: det_counts[d] for d in DETERMINANT_ORDER if d != "F"} | {"F": pure_f},
        "blends": blends, "pairs": pairs,
        "contents": {c: content[c] for c in CONTENT_CODES},
        "specials": dict(specials),
        "approach": {k: ".".join(v) for k, v in approach.items()},
        "L": lam, "M": M, "FM": FM, "m": m, "a": active, "p": passive, "Ma": ma, "Mp": mp,
        "FC": FC, "CF": CF, "C": C, "Cn": Cn, "WSumC": wsumc, "SumC'": sum_c_ach, "SumT": sum_t,
        "SumV": sum_v, "SumY": sum_y, "SumShading": sum_c_ach + sum_t + sum_v + sum_y,
        "EA": ea, "es": es, "AdjEs": adj_es, "EBStyle": style, "EBPer": eb_per,
        "Dscore": d_score(ea - es), "AdjD": d_score(ea - adj_es),
        "Afr": ratio(r_late, r_early), "Blends": len(blends), "ColShdBlends": col_shd,
        "CP": specials["CP"], "COP": specials["COP"], "AG": specials["AG"], "GHR": specials["GHR"],
        "PHR": specials["PHR"], "MOR": specials["MOR"], "PER": specials["PER"], "PSV": specials["PSV"],
        "AB": specials["AB"], "Fd": content["Fd"], "HumanCont": human, "PureH": content["H"],
        "Isolation": ratio(content["Bt"] + 2 * content["Cl"] + content["Ge"] + content["Ls"] + 2 * content["Na"], R),
        "Intellect": 2 * specials["AB"] + content["Art"] + content["Ay"],
        "Sum6": sum6, "Lvl2": lvl2, "WSum6": wsum6, "FAB2": specials["FAB2"],
        "M-": sum(1 for r in m_rows if r["fq"] == "-"), "Mnone": sum(1 for r in m_rows if r["fq"] == "none"),
        "XA%": ratio(sum(1 for r in rows if r["fq"] in good), R),
        "WDA%": ratio(sum(1 for r in wd if r["fq"] in good), len(wd)),
        "X-%": ratio(fq["-"], R), "X+%": ratio(fq["+"] + fq["o"], R), "Xu%": ratio(fq["u"], R),
        "S-": sum(1 for r in rows if r["location"]["space"] and r["fq"] == "-"),
        "P": sum(1 for r in rows if r["popular"]),
        "FQ+": fq["+"],
        "Egocentricity": ratio(3 * reflections + pairs, R), "FrrF": reflections, "FD": det_counts["FD"],
        "AnXy": content["An"] + content["Xy"],
    }


# --------------------------------------------------------------------------- constellations

def _lt(x: float | None, t: float) -> bool:
    return x is not None and x < t


def _gt(x: float | None, t: float) -> bool:
    return x is not None and x > t


def constellations(v: dict) -> list[dict]:
    R = v["R"]
    pti = [
        ("XA% < .70 and WDA% < .75", _lt(v["XA%"], 0.70) and _lt(v["WDA%"], 0.75)),
        ("X-% > .29", _gt(v["X-%"], 0.29)),
        ("Level 2 > 2 and FAB2 > 0", v["Lvl2"] > 2 and v["FAB2"] > 0),
        ("R < 17 and WSum6 > 12, or R > 16 and WSum6 > 17",
         (R < 17 and v["WSum6"] > 12) or (R > 16 and v["WSum6"] > 17)),
        ("M- > 1 or X-% > .40", v["M-"] > 1 or _gt(v["X-%"], 0.40)),
    ]
    depi = [
        ("FV+VF+V > 0 or FD > 2", v["SumV"] > 0 or v["FD"] > 2),
        ("Col-Shd Blends > 0 or S > 2", v["ColShdBlends"] > 0 or v["S"] > 2),
        ("3r+(2)/R > .44 and Fr+rF = 0, or 3r+(2)/R < .33",
         (_gt(v["Egocentricity"], 0.44) and v["FrrF"] == 0) or _lt(v["Egocentricity"], 0.33)),
        ("Afr < .46 or Blends < 4", _lt(v["Afr"], 0.46) or v["Blends"] < 4),
        ("SumShading > FM+m or SumC' > 2", v["SumShading"] > v["FM"] + v["m"] or v["SumC'"] > 2),
        ("MOR > 2 or 2AB+Art+Ay > 3", v["MOR"] > 2 or v["Intellect"] > 3),
        ("COP < 2 or Isolate/R > .24", v["COP"] < 2 or _gt(v["Isolation"], 0.24)),
    ]
    cdi = [
        ("EA < 6 or AdjD < 0", v["EA"] < 6 or v["AdjD"] < 0),
        ("COP < 2 and AG < 2", v["COP"] < 2 and v["AG"] < 2),
        ("WSumC < 2.5 or Afr < .46", v["WSumC"] < 2.5 or _lt(v["Afr"], 0.46)),
        ("Passive > Active + 1 or Pure H < 2", v["p"] > v["a"] + 1 or v["PureH"] < 2),
        ("SumT > 1 or Isolate/R > .24 or Food > 0", v["SumT"] > 1 or _gt(v["Isolation"], 0.24) or v["Fd"] > 0),
    ]
    scon = [
        ("FV+VF+V+FD > 2", v["SumV"] + v["FD"] > 2),
        ("Col-Shd Blends > 0", v["ColShdBlends"] > 0),
        ("3r+(2)/R < .31 or > .44", _lt(v["Egocentricity"], 0.31) or _gt(v["Egocentricity"], 0.44)),
        ("MOR > 3", v["MOR"] > 3),
        ("Zd > +3.5 or Zd < -3.5", v["Zd"] is not None and abs(v["Zd"]) > 3.5),
        ("es > EA", v["es"] > v["EA"]),
        ("CF + C > FC", v["CF"] + v["C"] > v["FC"]),
        ("X+% < .70", _lt(v["X+%"], 0.70)),
        ("S > 3", v["S"] > 3),
        ("P < 3 or P > 8", v["P"] < 3 or v["P"] > 8),
        ("Pure H < 2", v["PureH"] < 2),
        ("R < 17", R < 17),
    ]
    c = v["contents"]
    whole_human_animal = c["H"] + c["A"]
    part_human_animal = c["Hd"] + c["Ad"]
    hvi_first = ("FT+TF+T = 0 (required)", v["SumT"] == 0)
    hvi_rest = [
        ("Zf > 12", v["Zf"] > 12),
        ("Zd > +3.5", v["Zd"] is not None and v["Zd"] > 3.5),
        ("S > 3", v["S"] > 3),
        ("H+(H)+Hd+(Hd) > 6", v["HumanCont"] > 6),
        ("(H)+(A)+(Hd)+(Ad) > 3", c["(H)"] + c["(A)"] + c["(Hd)"] + c["(Ad)"] > 3),
        ("H+A : Hd+Ad < 4 : 1", part_human_animal > 0 and whole_human_animal / part_human_animal < 4),
        ("Cg > 3", c["Cg"] > 3),
    ]
    obs = [
        ("Dd > 3", v["Dd"] > 3),
        ("Zf > 12", v["Zf"] > 12),
        ("Zd > +3.0", v["Zd"] is not None and v["Zd"] > 3.0),
        ("Populars > 7", v["P"] > 7),
        ("FQ+ > 1", v["FQ+"] > 1),
    ]
    first4 = sum(met for _, met in obs[:4])
    all5 = sum(met for _, met in obs)
    xplus = v["X+%"] or 0
    obs_positive = (all5 == 5 or (first4 >= 2 and v["FQ+"] > 3) or (all5 >= 3 and xplus > 0.89)
                    or (v["FQ+"] > 3 and xplus > 0.89))
    hvi_count = sum(met for _, met in hvi_rest)

    def item(name, conds, threshold, positive, value=None):
        return {"name": name, "value": value if value is not None else sum(met for _, met in conds),
                "threshold": threshold, "positive": positive,
                "conditions": [{"label": label, "met": bool(met)} for label, met in conds]}

    n = lambda conds: sum(met for _, met in conds)  # noqa: E731
    return [
        item("PTI", pti, "> 3 (interpretive key)", n(pti) > 3),
        item("DEPI", depi, ">= 5", n(depi) >= 5),
        item("CDI", cdi, ">= 4", n(cdi) >= 4),
        item("S-CON", scon, ">= 8", n(scon) >= 8),
        item("HVI", [hvi_first] + hvi_rest, "item 1 + 4 others", hvi_first[1] and hvi_count >= 4,
             value=int(hvi_first[1]) + hvi_count),
        item("OBS", obs, "see rules", obs_positive),
    ]


# --------------------------------------------------------------------------- formatting

def fmt(x) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        if math.isinf(x):
            return "∞"
        if x.is_integer():
            return f"{x:.1f}"
        s = f"{x:.2f}"
        return s[1:] if s.startswith("0.") else s.replace("-0.", "-.")
    return str(x)


def sections(v: dict) -> list[dict]:
    def sec(title, pairs):
        return {"title": title, "items": [{"label": k, "value": val if isinstance(val, str) else fmt(val)}
                                          for k, val in pairs]}

    dq, fqx, mq, wdq = v["DQ"], v["FQx"], v["MQual"], v["WDQual"]
    sum_c_ach = v["SumC'"]
    fq_row = lambda d: " / ".join(f"{k} {d[k]}" for k in ("+", "o", "u", "-", "none"))  # noqa: E731
    return [
        sec("Location features", [
            ("Zf", v["Zf"]), ("ZSum", float(v["ZSum"])), ("ZEst", v["ZEst"]), ("W", v["W"]), ("D", v["D"]),
            ("W+D", v["W"] + v["D"]), ("Dd", v["Dd"]), ("S", v["S"])]),
        sec("Developmental quality", [(k, dq[k]) for k in ("+", "o", "v/+", "v")]),
        sec("Form quality (+ / o / u / - / none)", [
            ("FQx", fq_row(fqx)), ("MQual", fq_row(mq)), ("W+D", fq_row(wdq))]),
        sec("Determinants", [("Blends", ", ".join(v["blends"]) or "—")]
            + [(d, n) for d, n in v["determinants"].items()] + [("(2)", v["pairs"])]),
        sec("Contents", [(c, n) for c, n in v["contents"].items() if n] or [("—", "none coded")]),
        sec("Approach", list(v["approach"].items())),
        sec("Special scores", [
            ("Sum6", v["Sum6"]), ("Level 2", v["Lvl2"]), ("WSum6", v["WSum6"]),
            *[(s, v["specials"].get(s, 0)) for s in ("DV1", "DV2", "INC1", "INC2", "DR1", "DR2", "FAB1", "FAB2",
                                                  "ALOG", "CONTAM", "AB", "AG", "COP", "CP", "GHR", "PHR",
                                                  "MOR", "PER", "PSV")]]),
        sec("Core", [
            ("R", v["R"]), ("L", v["L"]), ("EB", f"{v['M']} : {fmt(v['WSumC'])}"), ("EA", v["EA"]),
            ("EBPer", v["EBPer"]), ("EB style", v["EBStyle"]),
            ("eb", f"{v['FM'] + v['m']} : {v['SumShading']}"), ("es", v["es"]), ("D", v["Dscore"]),
            ("Adj es", v["AdjEs"]), ("Adj D", v["AdjD"]), ("FM", v["FM"]), ("m", v["m"]),
            ("SumC'", v["SumC'"]), ("SumT", v["SumT"]), ("SumV", v["SumV"]), ("SumY", v["SumY"])]),
        sec("Affect", [
            ("FC : CF+C", f"{v['FC']} : {v['CF'] + v['C']}"), ("Pure C", v["C"]),
            ("SumC' : WSumC", f"{sum_c_ach} : {fmt(v['WSumC'])}"), ("Afr", v["Afr"]), ("S", v["S"]),
            ("Blends : R", f"{v['Blends']} : {v['R']}"), ("CP", v["CP"])]),
        sec("Interpersonal", [
            ("COP", v["COP"]), ("AG", v["AG"]), ("GHR : PHR", f"{v['GHR']} : {v['PHR']}"),
            ("a : p", f"{v['a']} : {v['p']}"), ("Food", v["Fd"]), ("SumT", v["SumT"]),
            ("Human Cont", v["HumanCont"]), ("Pure H", v["PureH"]), ("PER", v["PER"]),
            ("Isolation Index", v["Isolation"])]),
        sec("Ideation", [
            ("a : p", f"{v['a']} : {v['p']}"), ("Ma : Mp", f"{v['Ma']} : {v['Mp']}"),
            ("2AB+Art+Ay", v["Intellect"]), ("MOR", v["MOR"]), ("Sum6", v["Sum6"]), ("Lvl-2", v["Lvl2"]),
            ("WSum6", v["WSum6"]), ("M-", v["M-"]), ("M none", v["Mnone"])]),
        sec("Mediation", [
            ("XA%", v["XA%"]), ("WDA%", v["WDA%"]), ("X-%", v["X-%"]), ("S-", v["S-"]), ("P", v["P"]),
            ("X+%", v["X+%"]), ("Xu%", v["Xu%"])]),
        sec("Processing", [
            ("Zf", v["Zf"]), ("W : D : Dd", f"{v['W']} : {v['D']} : {v['Dd']}"), ("W : M", f"{v['W']} : {v['M']}"),
            ("Zd", v["Zd"]), ("PSV", v["PSV"]), ("DQ+", dq["+"]), ("DQv", dq["v"])]),
        sec("Self-perception", [
            ("3r+(2)/R", v["Egocentricity"]), ("Fr+rF", v["FrrF"]), ("SumV", v["SumV"]), ("FD", v["FD"]),
            ("An+Xy", v["AnXy"]), ("MOR", v["MOR"]),
            ("H : (H)+Hd+(Hd)", f"{v['contents']['H']} : {v['HumanCont'] - v['contents']['H']}")]),
    ]


def structural_summary(rows: list[dict]) -> tuple[dict, dict]:
    """Returns (variables, display summary)."""
    v = compute(rows)
    return v, {"sections": sections(v), "constellations": constellations(v)}
