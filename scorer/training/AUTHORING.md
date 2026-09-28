# Writing synthetic training records

These records bootstrap the Laya coder before any real, reviewer-corrected data exists.
They are **silver labels**: CS codes written by a model following these rules, not by a
trained examiner. Once real data is collected, it replaces them (see `README.md`).

## Record format

One JSON object per line in `synthetic/<name>.jsonl`:

```json
{"id": "c03-017", "card": 3, "orientation": "^", "location": "D",
 "verbatim": "two ppl lifting a pot",
 "inquiry": "here and here, the heads, legs, they bend down to pick it up. the pot is in the middle",
 "followups": [],
 "persona": "terse",
 "labels": {"validity": "genuine", "dq": "+", "determinants": ["Ma"], "pair": true,
            "contents": ["H", "Hh"], "special_scores": ["COP"], "fq_fallback": "u"}}
```

| Field | Values |
|---|---|
| `id` | unique; `c<card 2 digits>-<3 digits>` for card sets, `v<3 digits>` for the validity set |
| `card` | 1–10 |
| `orientation` | `^` upright, `v` upside down, `>` or `<` turned. Mostly `^`; about 1 in 10 turned. |
| `location` | `W`, `WS`, `D`, `DS`, `Dd`, `DdS`, or `Dd99`. Generic on purpose: the build script maps `D`/`Dd` to area numbers from the card's region map. Add `S` only when the answer uses the white space. |
| `verbatim` | what the person typed in the response phase |
| `inquiry` | what they typed for "what makes it look like that?" (where it is, and why) |
| `followups` | optional `[{"prompt", "answer"}]` for CS key-word follow-ups (e.g. they said "pretty") |
| `persona` | how the text is written; see the persona table below |
| `labels.validity` | `genuine`, `unserious`, `gibberish`, `refusal`, `off_task` |
| `labels.dq` | `+`, `o`, `v/+`, `v` |
| `labels.determinants` | a list; more than one is a blend. Movement always has a/p: `Ma`, `Mp`, `Ma-p`, `FMa`, `FMp`, `ma`, `mp`. Others: `F`, `FC`, `CF`, `C`, `Cn`, `FC'`, `C'F`, `C'`, `FT`, `TF`, `T`, `FV`, `VF`, `V`, `FY`, `YF`, `Y`, `Fr`, `rF`, `FD` |
| `labels.pair` | `true` for (2) |
| `labels.contents` | primary first: `H`, `(H)`, `Hd`, `(Hd)`, `Hx`, `A`, `(A)`, `Ad`, `(Ad)`, `An`, `Art`, `Ay`, `Bl`, `Bt`, `Cg`, `Cl`, `Ex`, `Fd`, `Fi`, `Ge`, `Hh`, `Ls`, `Na`, `Sc`, `Sx`, `Xy`, `Id` |
| `labels.special_scores` | `DV1`, `DV2`, `INC1`, `INC2`, `DR1`, `DR2`, `FAB1`, `FAB2`, `ALOG`, `CONTAM`, `AB`, `AG`, `COP`, `MOR`, `PER`, `CP` |
| `labels.fq_fallback` | `u` if the object fits the area's shape, `-` if it distorts it, `none` if no form is used (pure C, C', T, V, Y, or formless m) |

For `validity` other than `genuine`, only `validity` is needed. The other labels are ignored.

Run `python3 scorer/training/validate.py scorer/training/synthetic/<file>.jsonl` before finishing.

## Coding rules (Exner CS, condensed)

Code **only what the person reports**. Don't infer a determinant they didn't mention.

- **DQ.** `+` means two or more separate objects described as related ("two people *lifting* a pot",
  "a bat *flying over* a tree"), with at least one having specific form. `o` is one object with specific form.
  `v/+` is related objects, none with specific form ("clouds and smoke mixing"). `v` is no specific form
  (a cloud, blood, smoke, paint, a stain, "some kind of map").
- **Movement.** `M` is humans (or anything) in human activity or feeling. `FM` is animals doing
  animal things. `m` is inanimate or natural forces (falling, exploding, flowing, blowing in the wind).
  - `a` is active (running, fighting, lifting, dancing, flying, yelling, reaching).
  - `p` is passive (standing, sitting, looking, sleeping, hanging, floating, resting, whispering).
  - Animals doing human things are `M` and usually `FAB1`.
  - Human experience without an action ("a sad face") is `Mp` with `Hx`.
- **Chromatic colour.** Only on cards II, III, VIII, IX, X.
  - `FC`: shape first, colour adds to it ("a butterfly, and it's orange like a monarch").
  - `CF`: colour first, vague shape ("fire, because it's red and orange, spreading out").
  - `C`: colour alone ("blood, it's red").
  - `Cn`: only naming colours ("that's red and blue").
  - Colour used only to point ("the red part") is **not** a determinant.
  - On cards I, IV, V, VI, VII a reported chromatic colour is `CP`, not a colour determinant.
- **Achromatic colour.** Black, white or grey used as colour: `FC'` / `C'F` / `C'` ("a black bat, it's dark like one").
- **Shading.**
  - Texture: `FT`/`TF`/`T` ("fur, it looks soft and fuzzy").
  - Vista (depth from shading): `FV`/`VF`/`V` ("looking down into a canyon, the dark parts are deeper").
  - Diffuse shading: `FY`/`YF`/`Y` ("smoke, the different shades", "an X-ray, light and dark").
- **FD.** Depth from size or position alone, without shading ("a giant seen from below, the feet are big because they're closer").
- **Reflection.** `Fr`/`rF`: something reflected ("a bear looking at itself in the water"). A reflection is never also `(2)`.
- **Pair `(2)`.** Two identical objects based on the symmetry ("two dogs", "two women facing each other").
- **Contents.** The primary object comes first. Add secondary contents (the pot is `Hh`, clothes `Cg`, blood `Bl`).
  - An animal pelt or skin is `Ad`.
  - A mask is `(Hd)`.
  - Cartoon, monster and alien figures are `(H)` or `(A)`.
- **Special scores.**
  - `MOR`: dead, injured, ruined, sad or decaying.
  - `AG`: aggression happening now (fighting, attacking, an angry face glaring).
  - `COP`: clearly positive or cooperative interaction (helping, dancing together, playing together).
  - `INC1`: an impossible feature merged into one object ("a bat with hands", "a red bear"). `INC2` is bizarre.
  - `FAB1`: an implausible relationship ("two chickens playing basketball"). `FAB2`: impossible ("a man walking through a wall").
  - `DV1`: odd word use or redundancy ("a pair of two bugs"). `DV2`: a neologism.
  - `DR1`: an irrelevant tangent ("a butterfly, I hate those, they're gross"). `DR2`: derailed rambling.
  - `PER`: personal experience as justification ("I had one like that as a kid").
  - `AB`: symbolic meaning ("a heart that means love").
  - `ALOG`: strained logic ("it must be the north pole because it's at the top").
  - `CONTAM`: two percepts fused ("a butterfly face").
- **fq_fallback.** Would most people see this object in that area without distorting its shape? `u` if yes (easy to see), `-` if the object doesn't match the area's contours.

## Cards (standard CS areas, for writing realistic answers)

- **I** (grey-black). W: bat or butterfly (Popular), a moth, an eagle, a mask with white-space eyes (WS). Centre: a woman's body, a beetle. Sides: winged people, angels.
- **II** (black with red). Black sides: two dogs or bears touching noses (Popular), elephants, clowns clapping. Top red: red hats, socks, flames. Bottom red: a butterfly, blood, fire, a vagina (Sx). Centre white: a spaceship, a lamp, a spinning top (DS).
- **III** (black with red). The black figures: two people or waiters bending over a pot or basket (Popular), cannibals, aliens. Red middle: a bow tie or butterfly. Red sides: monkeys hanging, blood drips, a fetus.
- **IV** (dark, heavy shading). W: a giant, monster or Bigfoot seen from below (Popular, often FD), an animal hide (texture). Sides at the bottom: boots. Bottom centre: a tree stump, an animal head. Top: a flower bud.
- **V** (black). W: bat or butterfly (Popular), two animals butting heads, a person in a cape. Top: rabbit ears or antennae. Side edges: legs or crocodile heads.
- **VI** (grey, soft shading). W or the large lower part: an animal skin or rug (Popular, often texture). Top: a totem, guitar neck, feathered wings, a phallus (Sx). Centre line: a spine or river.
- **VII** (light grey). Upper parts: two girls' or women's heads (Popular), rabbits, pigtails. W: two women facing each other, dancers, clouds (shading Y). Centre bottom: a butterfly or vagina. Centre white space: a lamp, a vase, a map (DS).
- **VIII** (pastel colours). Pink sides: animals climbing, bears or cats (Popular). Top grey-green: a tree, mountain or tent. Blue middle: flags, a ribcage, a shirt. Pink-orange bottom: ice cream, a flower, a butterfly. W: a coat of arms, an emblem, an anatomy chart.
- **IX** (orange, green, pink). Orange top: witches or wizards (Popular), lobsters, deer. Green middle: bushes, clouds, maps, faces. Pink bottom: baby heads, fire, a sunset. Centre white space: a vase, violin or spine (DS). W: an explosion, a nuclear blast, a fountain.
- **X** (many colours, scattered). Blue sides: crabs or spiders (Popular). Pink long areas: caterpillars, tissue, faces. Yellow: lions, dogs, birds, flowers. Green bottom: caterpillars, snakes, a rabbit head. Grey top: the Eiffel Tower, insects on a stick. W: an underwater scene, a garden, fireworks, a party.

## Personas (how the text reads)

| persona | style |
|---|---|
| `standard` | normal adult sentences |
| `terse` | typed on a phone: lowercase, fragments, no punctuation ("2 dogs kissing, noses here") |
| `nonnative` | broken or unusual English ("is like two man, they are carry something") |
| `typo` | several real misspellings ("a buterfly, wigns out to the sied") |
| `elaborate` | long and detailed, several parts named |
| `odd_genuine` | sincere but unusual, morbid, sexual, pop-culture or funny in tone, yet still a real percept of the blot ("darth vader's helmet", "my ex's angry face lol, the eyes here") |
| `unserious`, `gibberish`, `refusal`, `off_task` | the non-genuine validity classes |
