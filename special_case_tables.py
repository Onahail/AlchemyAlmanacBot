# special_case_tables.py

dragon_tea_table = ("```"
              "DRAGON   FIRE   SPELL        MEDICINE\n"
              " DUST   DAMAGE  RANGE        STRENGTH\n"
              " x1     4d6     15-ft cone   ★★\n"
              " x2     6d6     30-ft cone   ★★★\n"
              " x3     8d6     45-ft cone   ★★★★  \n"
              " x4     12d6    60-ft cone   ★★★★★```")


prismatic_balm_table = (
    "```"
    "DRAGON     DAMAGE TYPE\n"
    "Black      Acid\n"
    "Blue       Lightning\n"
    "Brass      Fire\n"
    "Bronze     Lightning\n"
    "Copper     Acid\n"
    "Gold       Fire\n"
    "Green      Poison\n"
    "Red        Fire\n"
    "Silver     Cold\n"
    "White      Cold"
    "```"
)


mastermind_table = (
    "```"
    "AVAILABLE             MAXIMUM\n"
    "  SPELL                 USES    SAVE DC\n"
    "levitate                3       15\n"
    "telekinesis             1       20\n"
    "plane shift (self only) 1       25"
    "```"
)

giant_strength_table = (
    "```"
    "   GIANT     STRENTH   MEDICINE\n"
    "HEARTSBLOOD   SCORE    STRENGTH\n"
    "× 1            21       ★★\n"
    "× 2            23       ★★★\n"
    "× 3            27       ★★★★\n"
    "× 4            29       ★★★★★\n"
    "```"
)

creature_skill_checks = {
    "Creature Type": [
        "Aberrations, Elementals, and Fey",
        "Beasts, Dragons, and Monstrosities",
        "Celestials, Fiends, and Undead",
        "Constructs",
        "Giants and Humanoids",
        "Oozes and Plants"
    ],
    "Skill": [
        "Arcana",
        "Survival",
        "Religion",
        "Investigation",
        "Medicine",
        "Nature"
    ]
}