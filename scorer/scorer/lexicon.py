"""Word lists for the rule-based coder.

Keys are base forms (see `text.candidates`); multi-word keys are phrases.
These are deliberately small and conservative: the RuleCoder is a
deterministic baseline, not a substitute for a trained model or an examiner.
"""

from __future__ import annotations

# --- Contents -----------------------------------------------------------------

_CONTENT_WORDS: dict[str, str] = {
    # (H) fictional / mythological humans
    "(H)": """angel devil demon ghost witch giant monster alien fairy elf gnome troll goblin vampire
        zombie wizard god goddess genie ogre superhero batman santa snowman puppet doll clown-doll
        mermaid cyclops cherub spirit phantom sorcerer warlock ninja-turtle cartoon-character
        scarecrow gargoyle martian creature-from-space""",
    # H whole humans
    "H": """person man woman lady girl boy child baby human dancer waiter waitress soldier king queen
        prince princess clown indian native chef cook twin gentleman guy kid mother father sister
        brother friend priest monk nun doctor nurse farmer sailor pirate knight cowboy singer
        musician drummer skier swimmer athlete player figure people-figure acrobat ballerina
        butler maid bride groom old-woman old-man teenager toddler infant crowd lover couple-of-people
        hunter warrior dwarf""",
    # (Hd) fictional human details
    "(Hd)": "mask devil-face monster-face jack-o-lantern",
    # Hd human details
    "Hd": """head face hand arm leg foot finger eye nose mouth lip ear hair beard mustache moustache chin
        cheek forehead tooth knee thumb fist torso shoulder neck profile eyebrow eyelash
        elbow wrist ankle toe heel lap belly navel""",
    # (A) fictional / mythological animals
    "(A)": """dragon unicorn pegasus griffin gryphon phoenix teddy-bear stuffed-animal cartoon-animal
        mickey-mouse bugs-bunny godzilla hydra sea-monster""",
    # Ad animal details
    "Ad": """tusk horn antler paw claw snout muzzle mandible fang beak tail hoof mane antenna jowl
        pincer feeler whisker trunk-of-an-elephant skin hide pelt fur-rug bearskin gill fin feather
        wing tentacle stinger shell""",
    # A whole animals
    "A": """animal creature bat butterfly moth bird eagle crow raven owl chicken rooster hen duck swan
        penguin parrot dog puppy cat kitten lion tiger leopard panther cheetah bear wolf fox rabbit
        bunny hare mouse rat squirrel beaver raccoon deer elk moose reindeer horse pony cow bull ox
        pig sheep lamb goat camel elephant rhino rhinoceros hippo hippopotamus giraffe zebra monkey
        ape gorilla chimpanzee frog toad lizard snake turtle tortoise crocodile alligator dinosaur fish
        shark whale dolphin seal walrus octopus squid crab lobster shrimp spider insect bug beetle ant
        bee wasp dragonfly mosquito scorpion worm caterpillar snail slug jellyfish starfish seahorse
        cockroach grasshopper cricket ladybug hamster weasel ferret otter skunk badger hedgehog
        porcupine kangaroo koala bison buffalo donkey mule llama vulture hawk falcon pelican flamingo
        peacock turkey pigeon sparrow hummingbird tadpole salamander poodle bulldog cub calf fawn
        mole bug-eyed-creature stingray ray manta iguana chameleon crayfish mantis flea tick louse
        platypus lemur sloth armadillo anteater jaguar lynx puma cougar hyena jackal coyote
        stag doe ram""",
    "An": """skeleton bone rib ribcage pelvis spine backbone vertebra skull heart lung liver kidney
        stomach intestine brain uterus organ muscle vein artery womb bladder anatomy tissue
        hip-bone breastbone sternum collarbone jaw jawbone trachea larynx""",
    "Xy": "xray mri scan ultrasound radiograph",
    "Art": """painting drawing sculpture statue emblem crest logo badge coat-of-arms decoration ornament
        design tattoo art abstract-art pattern carving figurine inkblot-art chandelier stained-glass
        insignia""",
    "Ay": """totem totem-pole pyramid sphinx headdress viking samurai pharaoh egyptian aztec mayan
        tribal mummy""",
    "Bl": "blood gore",
    "Bt": """flower tree leaf plant bush root seed petal rose tulip orchid lily stem branch vine moss
        mushroom fungus grass fern cactus pine palm blossom bud weed seaweed algae twig pollen
        orchard""",
    "Cg": """dress coat jacket hat cap boot shoe glove shirt skirt pants trouser bowtie bow-tie necktie
        cape robe gown helmet crown collar sleeve uniform costume veil scarf belt sock bra apron cloak
        hood tuxedo boots bikini""",
    "Cl": "cloud",
    "Ex": "explosion blast firework eruption detonation",
    "Fi": "fire flame smoke spark ember campfire",
    "Fd": """food meat steak ice-cream candy fruit apple banana pear cake pizza bread egg soup vegetable
        carrot broccoli lollipop cookie sandwich bacon sausage ham cheese popcorn pie dessert
        drumstick roast""",
    "Ge": "map country continent coastline globe",
    "Hh": """lamp chair table bed vase pot pan cup bowl fork spoon rug carpet curtain pillow candle
        candlestick bell bottle jar basket clock broom bucket blanket towel fireplace sofa couch key
        mirror-frame teapot kettle""",
    "Ls": """mountain hill valley cave rock desert island canyon cliff coast shore beach swamp landscape
        scenery underwater reef terrain forest jungle""",
    "Na": """sun moon star sky water river lake sea ocean wave rainbow snow ice rain storm lightning
        night sunset sunrise weather stream waterfall pond puddle fog mist volcano earth planet
        galaxy universe space""",
    "Sc": """airplane plane jet rocket spaceship ship boat car truck bicycle bike train building house
        castle church tower bridge robot machine tool gun weapon sword arrow bomb anchor instrument
        guitar violin drum piano tank helicopter submarine satellite microscope telescope computer
        phone fountain monument pole pipe trophy chalice hourglass shield cannon spear axe hammer
        wrench scissors pliers abacus arch gate fence road flag kite balloon umbrella parachute
        wheel engine motor astrodome catamaran bellows cabin pagoda temple lighthouse windmill
        chandelier-frame lantern torch vehicle ufo flying-saucer""",
    "Sx": "penis vagina vulva breast nipple genital genitals phallus testicle sex intercourse",
}


def _explode(spec: str) -> list[str]:
    return [w.replace("-", " ") for w in spec.split()]


# Base form -> content code. Earlier categories win (fictional before real,
# details before wholes only where the word is unambiguous).
CONTENT: dict[str, str] = {}
for _code, _spec in _CONTENT_WORDS.items():
    for _w in _explode(_spec):
        CONTENT.setdefault(_w, _code)

HUMAN_CONTENTS = frozenset({"H", "(H)", "Hd", "(Hd)"})
ANIMAL_CONTENTS = frozenset({"A", "(A)", "Ad", "(Ad)"})
WHOLE_HUMAN = frozenset({"H", "(H)"})
WHOLE_ANIMAL = frozenset({"A", "(A)"})

# Parts that are ambiguous between humans and animals ("head", "eyes", "legs"):
# they only become Hd/Ad when no whole object is named.
SHARED_PARTS = frozenset(_explode("head eye leg body mouth nose ear tooth foot face neck back arm tail wing"))
# Parts that are human-only; on an animal they are an incongruity (INC).
HUMAN_ONLY_PARTS = frozenset(_explode("hand finger fist thumb eyebrow eyelash lip beard mustache moustache knee elbow"))
# Inanimate "wholes" whose parts should not be coded as Hd/Ad.
INVERTEBRATES = frozenset(_explode(
    "butterfly moth insect bug beetle ant bee wasp fly dragonfly mosquito spider scorpion crab lobster "
    "shrimp worm caterpillar snail slug jellyfish starfish cockroach grasshopper cricket ladybug mantis flea tick"))

# Words that only name an object when preceded by a determiner/number (otherwise verbs).
NOUN_NEEDS_DETERMINER = {"fly": "A", "watch": "Sc", "face": "Hd", "seal": "A", "ram": "A", "hide": "Ad",
                         "ray": "A", "doe": "A", "stag": "A", "star": "Na", "space": "Na", "shell": "Ad"}
DETERMINERS = frozenset(_explode(
    "a an the one two three some this that these those big small little large huge tiny dead house giant "
    "his her its their my of like"))

HUMAN_EXPERIENCE = frozenset(_explode(
    "love hate anger angry happiness happy sad sadness fear afraid scared joy joyful depressed depression "
    "lonely loneliness emotion feeling grief grieving jealous jealousy ashamed shame proud pride worried "
    "anxious anxiety calm peaceful surprised shocked frightened terrified miserable unhappy smell stink"))

# Formless things that usually carry no specific form demand (DQ v).
FORMLESS = frozenset(_explode(
    "cloud blood smoke water paint fire flame map rock ice mud dirt ink stain splash splatter puddle sky sea "
    "ocean lake snow rain fog mist explosion blast abstract design color landscape scenery island "
    "coastline terrain gore food meat dust sand fluid liquid goo slime stuff smudge"))

GROUP_WORDS = frozenset(_explode("group herd flock pack crowd bunch swarm family team school colony"))

# --- Determinants ---------------------------------------------------------------

# Movement verbs: base -> "a" (active) or "p" (passive).
MOVEMENT: dict[str, str] = {}
for _w in _explode("""fight run jump fly dance lift argue yell scream shout attack kill hit kick punch push pull
        climb chase grab reach glare swim leap spin crawl walk eat throw carry struggle pound bang play wave
        shake tear rip bite sting peck hunt roar growl howl bark sing laugh clap charge race rush dive swoop
        explode erupt burst shoot spray splash blow crash smash strike stab march gallop sprint jog skip
        chop pounce wrestle tug drag bounce twirl rotate turn chew lick fling squeeze drink cook build
        work slide swing ride sail soar"""):
    MOVEMENT[_w] = "a"
for _w in _explode("""stand sit look sleep hang float rest whisper sigh lie lean wait watch gaze stare dream think
        relax kneel pose bend talk glide drift hover balance peek smile cry drip flow melt sink droop sag
        dangle perch crouch squat stretch hug kiss touch meet greet bow pray meditate listen read spread
        hold face nap lounge recline doze sunbathe weep bleed ooze trickle seep sway fall hide
        peer contemplate daydream wonder admire"""):
    MOVEMENT[_w] = "p"
# "look like" / "looks like" is how people describe percepts, not movement.
NON_MOVEMENT_AFTER = {"look": {"like", "as", "kind", "sort", "similar", "a", "an", "to", "more", "less"},
                      "face": {"of"}}
# Verbs only humans do: an animal doing them is M (and, for 2+ animals, FAB).
HUMAN_ONLY_VERBS = frozenset(_explode(
    "dance argue talk whisper sing pray clap read cook meditate kiss hug toast gossip laugh smile wave "
    "greet bow chat daydream contemplate write shake hands play cards"))
# Verbs describing inanimate/natural forces (m) regardless of subject.
INANIMATE_VERBS = frozenset(_explode(
    "explode erupt burst blow drip flow melt spray splash ooze trickle seep crash sink fall dangle float"))

CHROMATIC = frozenset(_explode(
    "red pink orange yellow green blue purple violet brown turquoise gold golden crimson scarlet maroon "
    "salmon peach beige color colored colorful rosy bluish reddish greenish yellowish pinkish orangey "
    "orangish purplish magenta lavender lilac teal cyan"))
ACHROMATIC = frozenset(_explode("black gray white silver dark blackness grayish whitish charcoal"))
TEXTURE = frozenset(_explode(
    "fur furry fuzzy soft rough smooth hairy feathery velvety silky woolly wooly texture feel slimy fluffy "
    "prickly bumpy coarse spiky textured leathery scaly slippery touchable"))
SHADING = frozenset(_explode(
    "shading shaded shade shadow shadowy light-and-dark lighter darker different-shades hazy "
    "misty murky faded smoky mottled blurry transparent see-through"))
DEPTH = frozenset(_explode(
    "depth deep far distance far-away in-the-distance behind in-front 3d three-dimensional looking-down "
    "from-above from-below looking-into further background foreground perspective receding"))
REFLECTION = frozenset(_explode("reflection reflected reflecting reflect mirror mirror-image"))
# Form-demand words: naming parts or outline means the percept uses form.
FORM_WORDS = frozenset(_explode(
    "shape shaped form outline contour head body wing leg arm tail eye ear nose mouth point edge"))

# --- Special scores ---------------------------------------------------------------

MORBID = frozenset(_explode(
    "dead death die dying broken break torn tear crushed crush squashed squash flattened injured injury hurt "
    "wounded wound sad depressed depressing gloomy rotten rot decayed decaying bleeding bleed damaged damage "
    "destroyed killed mangled splattered ruined sick diseased deformed withered wilted tattered rotting "
    "skinned run-over roadkill carcass corpse scar scarred weeping crying lonely miserable unhappy burst "
    "bitten dismembered severed decapitated stabbed burned burnt shot dried-up deflated smashed ripped "
    "exhausted suffering pain painful sorrow grieving mourning"))
AGGRESSIVE = frozenset(_explode(
    "fight attack kill hit punch kick stab shoot strike war battle glare snarl threaten rip-apart "
    "tear-apart destroy smash choke strangle argue yell-at scream-at charge-at maul claw-at "
    "angry furious rage"))
COOPERATIVE_VERBS = frozenset(_explode(
    "dance play help share talk lift work cook sing hug kiss toast cheer build carry hold-hands shake-hands "
    "greet celebrate high-five chat whisper"))
TOGETHER = frozenset(_explode("together each-other one-another both-of-them"))
PERSONAL = ("i have seen", "i've seen", "i saw", "i had one", "i remember", "reminds me of when",
            "i know this from", "we had", "we used to", "when i was", "in my", "my own", "like mine",
            "my dad", "my mom", "my mother", "my father", "my house", "my dog", "my cat")
ABSTRACT = frozenset(_explode(
    "symbol symbolize symbolic represent stand-for love hate evil peace freedom hope "
    "good-and-evil harmony eternity soul essence-of concept-of"))
DEVIANT_VERBALIZATIONS = ("pair of two", "two twins", "couple of two", "round circle", "square box",
                          "tiny little small", "twin brothers twins")
PAIR_WORDS = ("two", "both", "pair", "couple", "twins", "each side", "on the sides", "on each side",
              "either side", "one on each side", "on both sides", "the sides")
RELATION_WORDS = frozenset(_explode(
    "with hold on on-top-of next-to beside between behind in-front-of around inside under over "
    "fight carry chase attached-to ride eat hug kiss touch face together each-other against "
    "toward towards into onto at climb push pull lift"))

# --- Follow-up (inquiry) keywords ------------------------------------------------------

FOLLOWUP_KEYWORDS = ("pretty", "beautiful", "ugly", "colorful", "bloody", "fiery", "fluffy", "furry", "soft",
                     "rough", "smooth", "velvety", "dark", "deep", "far", "shadowy", "transparent",
                     "glowing", "reflection", "reflected", "dirty", "muddy", "messy")
LOCATION_WORDS = frozenset(_explode(
    "here there top bottom side sides middle center centre whole all this that left right upper lower "
    "part area edge these those red black white gray blue green pink orange yellow brown inside outside "
    "above below up down around corner point tip end half entire everything card blot"))
