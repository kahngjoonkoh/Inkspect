"""Rule-based interpretation following the CS interpretive search strategy.

The first positive key variable fixes the order in which the clusters are
reviewed. Each finding is a fixed sentence tied to a threshold, so the output
is reproducible and auditable. No model writes free-form text here.
"""

CLUSTER_ORDERS = [
    ("PTI > 3", lambda v, c: c["PTI"]["value"] > 3,
     ["Ideation", "Mediation", "Processing", "Controls", "Affect", "Self-perception", "Interpersonal"]),
    ("DEPI > 5 and CDI > 3", lambda v, c: c["DEPI"]["value"] > 5 and c["CDI"]["value"] > 3,
     ["Interpersonal", "Self-perception", "Controls", "Affect", "Processing", "Mediation", "Ideation"]),
    ("DEPI > 5", lambda v, c: c["DEPI"]["value"] > 5,
     ["Affect", "Controls", "Self-perception", "Interpersonal", "Processing", "Mediation", "Ideation"]),
    ("D < Adj D", lambda v, c: v["Dscore"] < v["AdjD"],
     ["Controls", "Situational stress", "Affect", "Self-perception", "Interpersonal", "Processing",
      "Mediation", "Ideation"]),
    ("CDI > 3", lambda v, c: c["CDI"]["value"] > 3,
     ["Controls", "Interpersonal", "Self-perception", "Affect", "Processing", "Mediation", "Ideation"]),
    ("Adj D < 0", lambda v, c: v["AdjD"] < 0,
     ["Controls", "Affect", "Self-perception", "Interpersonal", "Processing", "Mediation", "Ideation"]),
    ("Lambda > .99", lambda v, c: v["L"] > 0.99,
     ["Processing", "Mediation", "Ideation", "Controls", "Affect", "Self-perception", "Interpersonal"]),
    ("Fr+rF > 0", lambda v, c: v["FrrF"] > 0,
     ["Self-perception", "Interpersonal", "Controls", "Affect", "Processing", "Mediation", "Ideation"]),
    ("EB introversive", lambda v, c: v["EBStyle"] == "Introversive",
     ["Ideation", "Processing", "Mediation", "Controls", "Affect", "Self-perception", "Interpersonal"]),
    ("EB extratensive", lambda v, c: v["EBStyle"] == "Extratensive",
     ["Affect", "Self-perception", "Interpersonal", "Controls", "Processing", "Mediation", "Ideation"]),
    ("p > a + 1", lambda v, c: v["p"] > v["a"] + 1,
     ["Ideation", "Processing", "Mediation", "Controls", "Self-perception", "Interpersonal", "Affect"]),
    ("HVI positive", lambda v, c: c["HVI"]["positive"],
     ["Ideation", "Processing", "Mediation", "Controls", "Self-perception", "Interpersonal", "Affect"]),
    ("OBS positive (tertiary)", lambda v, c: c["OBS"]["positive"],
     ["Processing", "Mediation", "Ideation", "Controls", "Affect", "Self-perception", "Interpersonal"]),
]
DEFAULT_ORDER = ["Controls", "Affect", "Self-perception", "Interpersonal", "Processing", "Mediation", "Ideation"]


def _findings(v: dict, c: dict) -> dict[str, list[str]]:
    f: dict[str, list[str]] = {k: [] for k in DEFAULT_ORDER + ["Situational stress"]}

    def add(cluster: str, cond: bool, text: str) -> None:
        if cond:
            f[cluster].append(text)

    def gt(x, t):
        return x is not None and x > t

    def lt(x, t):
        return x is not None and x < t

    add("Controls", v["AdjD"] < 0, "Adj D is below zero: in CS terms, a chronic overload of demands relative to "
        "available resources, with vulnerability to losing control under stress.")
    add("Controls", v["AdjD"] > 0, "Adj D is above zero: resources appear sufficient for the demands being felt.")
    add("Controls", v["AdjD"] == 0, "Adj D is zero, the most common value: capacity for control is in the usual range.")
    add("Controls", v["EA"] < 6, "EA is low (< 6): fewer organised resources are available than is typical.")
    add("Controls", c["CDI"]["positive"],
        "CDI is positive: difficulty coping with everyday social demands is suggested.")
    add("Situational stress", v["Dscore"] < v["AdjD"], "D is lower than Adj D: current situational stress "
        "(m and Y) appears to be adding to the load.")
    add("Affect", c["DEPI"]["positive"], "DEPI is positive: the record has features associated with depressive "
        "or affective disruption.")
    add("Affect", lt(v["Afr"], 0.50), "Afr is low: a tendency to avoid emotional stimulation.")
    add("Affect", gt(v["Afr"], 0.80), "Afr is high: marked interest in, or pull toward, emotional stimulation.")
    add("Affect", v["CF"] + v["C"] > v["FC"] + 1, "CF+C exceeds FC: feelings are expressed with less modulation "
        "than is typical for adults.")
    add("Affect", v["FC"] > (v["CF"] + v["C"]) * 2 and v["FC"] > 1, "FC clearly exceeds CF+C: emotional "
        "expression tends to be well modulated, perhaps overly controlled.")
    add("Affect", v["C"] > 0, "Pure C is present: at times emotion may be expressed with little control.")
    add("Affect", v["SumC'"] > v["WSumC"], "SumC' exceeds WSumC: feelings may be held in (constrained affect).")
    add("Affect", v["S"] > 2, "S > 2: an oppositional or angry set toward the environment is suggested.")
    add("Affect", v["ColShdBlends"] > 0, "Colour-shading blends are present: mixed or ambivalent feelings.")
    add("Self-perception", gt(v["Egocentricity"], 0.44), "3r+(2)/R is high: considerable self-focus.")
    add("Self-perception", lt(v["Egocentricity"], 0.33), "3r+(2)/R is low: a less favourable view of the self "
        "when compared with others.")
    add("Self-perception", v["FrrF"] > 0, "Reflection responses: a narcissistic-like tendency to overvalue "
        "personal worth.")
    add("Self-perception", v["MOR"] > 2, "MOR > 2: a pessimistic or damaged sense of self is suggested.")
    add("Self-perception", v["SumV"] > 0, "Vista responses: painful self-inspection may be present.")
    add("Self-perception", v["AnXy"] > 2, "An+Xy > 2: unusual body concern.")
    add("Interpersonal", v["COP"] >= 2 and v["AG"] <= 1, "COP >= 2 with few AG: interactions are expected to "
        "be positive and cooperative.")
    add("Interpersonal", v["AG"] > 2, "AG > 2: aggressive behaviour in interactions may be seen as natural.")
    add("Interpersonal", v["SumT"] == 0, "T = 0: needs for closeness may be less recognised or expressed "
        "(the most common deviation in the CS reference sample).")
    add("Interpersonal", v["SumT"] > 1, "T > 1: strong unmet needs for closeness.")
    add("Interpersonal", v["HumanCont"] < 4, "Human content is low: less interest in people than is typical.")
    add("Interpersonal", v["PHR"] > v["GHR"], "PHR exceeds GHR: interpersonal behaviour may be less adaptive.")
    add("Interpersonal", gt(v["Isolation"], 0.25), "Isolation index is elevated: social isolation is suggested.")
    add("Interpersonal", v["Fd"] > 0, "Food content: dependency-oriented behaviour may be present.")
    add("Processing", v["Zd"] is not None and v["Zd"] > 3.0, "Zd > +3.0: overincorporation, investing extra "
        "effort in scanning the field.")
    add("Processing", v["Zd"] is not None and v["Zd"] < -3.0, "Zd < -3.0: underincorporation, a hasty and "
        "sometimes careless scanning of the field.")
    add("Processing", v["DQ"]["v"] > 1, "DQv > 1: some processing is less mature or less precise.")
    add("Processing", v["PSV"] > 1, "PSV > 1: difficulty shifting attention.")
    add("Processing", v["Dd"] > 3, "Dd > 3: attention to unusual details.")
    add("Mediation", lt(v["XA%"], 0.70), "XA% is low: translation of input is less conventional or accurate.")
    add("Mediation", gt(v["X-%"], 0.20), "X-% > .20: more perceptual distortion than is typical.")
    add("Mediation", v["P"] < 4, "Few Popular responses: less conventional responding in obvious situations.")
    add("Mediation", v["P"] > 7, "Many Popular responses: strong concern with being conventional.")
    add("Mediation", gt(v["Xu%"], 0.25), "Xu% is elevated: an individualistic way of translating input.")
    add("Ideation", c["PTI"]["value"] > 3, "PTI > 3: signs of disordered thinking or perception are prominent.")
    add("Ideation", v["WSum6"] > 17, "WSum6 is high: thinking may be marked by cognitive slippage.")
    add("Ideation", v["p"] > v["a"] + 1, "p > a+1: a passive ideational set.")
    add("Ideation", v["Mp"] > v["Ma"], "Mp > Ma: a tendency to substitute fantasy for action.")
    add("Ideation", v["Intellect"] > 5, "2AB+Art+Ay > 5: intellectualisation is used to manage affect.")
    add("Ideation", v["M-"] > 0, "M- present: some ideation may be peculiar or distorted.")
    for cluster, items in f.items():
        if not items and cluster != "Situational stress":
            items.append("No notable deviations were found in the variables reviewed for this cluster.")
    return f


def interpret(v: dict, constellations: list[dict], placeholder_regions: bool) -> dict:
    c = {item["name"]: item for item in constellations}
    key, order = "No key variable positive", DEFAULT_ORDER
    for label, test, cluster_order in CLUSTER_ORDERS:
        if test(v, c):
            key, order = label, cluster_order
            break
    findings = _findings(v, c)
    caveats = [
        "This is an automated, rule-based reading of an automatically coded record. It is not a clinical "
        "assessment or diagnosis and must not be used as one.",
        "Interpretive statements follow Comprehensive System conventions for adults; the norms may not apply "
        "to this person or to online self-administration.",
    ]
    if not v["valid"]:
        caveats.insert(0, f"R = {v['R']} is below 14, so by CS rules the record is not interpretively valid.")
    if v["L"] > 0.99 and v["R"] < 17:
        caveats.append("High Lambda with a short record: the protocol may reflect a guarded or defensive approach.")
    if placeholder_regions:
        caveats.append("Location areas come from placeholder region maps, so location, Form Quality, Popular and "
                       "Z values are approximate.")
    return {
        "strategy": " → ".join(order),
        "key_variable": key,
        "clusters": [{"name": name, "findings": findings[name]} for name in order],
        "caveats": caveats,
    }
