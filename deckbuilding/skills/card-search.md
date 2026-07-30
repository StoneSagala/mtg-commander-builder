# Skill: /card-search

## What This Skill Does

Translates a plain-language description of a needed card effect into a Scryfall query, runs the search, and returns a filtered shortlist of the best matches ranked by relevance to the specific deck.

**Trigger:** Use when you need to find cards for a specific function and aren't sure what exists.

---

## Inputs Required

- What the card needs to DO (plain language)
- Color identity constraints
- Format (default: Commander)
- Budget ceiling (if any)
- Deck context — what strategy is this for?

---

## The Search Workflow

### Step 1: Translate the Need to Scryfall Syntax

Convert the plain-language description into a Scryfall query.

**Process:**
1. Identify the mechanical keyword (draw, destroy, counter, create token, add mana, etc.)
2. Apply color, CMC, type, and format constraints
3. Add `order:edhrec` for Commander searches — sorts by community popularity

**Common translations:**

| Need | Scryfall Query |
|------|---------------|
| Black 1-mana hand disruption | `t:creature c:b cmc=1 o:discard f:commander` |
| Green ramp that fetches a basic land | `o:"basic land" o:search c:g t:sorcery cmc<=3 f:commander` |
| Cheap blue counter for non-creature spells | `o:counter t:instant c:u cmc<=2 -o:creature f:commander` |
| Mana rocks for Commander | `t:artifact o:"add" cmc<=3 f:commander order:edhrec` |
| White removal under $2 | `t:instant o:exile t:creature c:w usd<=2 f:commander` |
| Tribal synergy pieces | `(t:[TRIBE] or o:"[TRIBE]") id<=[COLORS] f:commander order:edhrec` |
| Cards that copy spells | `o:"copy" (t:instant or t:sorcery) id<=[COLORS] f:commander order:edhrec` |

---

### Step 2: Run the Search

```bash
python scripts/fetch-card-data.py --query "[scryfall query]"
```

---

### Step 3: Filter and Rank Results

Raw results often return 20–100+ cards. Cut to the best 5–10:

1. **Format legality** — cut anything not legal
2. **Rate** — does the effect justify the mana cost?
3. **Synergy** — how well does this work with the specific deck?
4. **Budget** — rank affordable options higher if constrained
5. **EDHREC rank** — community-validated for Commander

---

### Step 4: Check Known Staples First

For common functions, established staples should be mentioned before alternatives:

| Function | Staples |
|----------|---------|
| Targeted removal | Swords to Plowshares, Path to Exile, Fatal Push, Generous Gift, Beast Within |
| Board wipes | Wrath of God, Damnation, Cyclonic Rift, Toxic Deluge, Supreme Verdict |
| Counterspells | Counterspell, Arcane Denial, Mana Drain, Force of Will, Fierce Guardianship |
| Card draw engines | Rhystic Study, Mystic Remora, Phyrexian Arena, Sylvan Library, The One Ring |
| Ramp (green) | Sol Ring, Arcane Signet, Cultivate, Kodama's Reach, Farseek, Nature's Lore |
| Tutors | Demonic Tutor, Vampiric Tutor, Enlightened Tutor, Mystical Tutor, Worldly Tutor |
| Commander protection | Lightning Greaves, Swiftfoot Boots, Heroic Intervention, Sylvan Safekeeper |

If a known staple fits, mention it first even if the search returns other options.

---

## Scryfall Syntax Reference

### Card Types
```
t:creature / t:instant / t:sorcery / t:enchantment / t:artifact / t:land / t:planeswalker
t:legendary    t:basic    t:elf    t:zombie    t:dragon
t:"legendary creature"   # compound types need quotes
```

### Colors
```
c:w  c:u  c:b  c:r  c:g  c:m  c:c        # exact color match
c<=ub                                       # contains only blue and/or black
c>=rg                                       # contains at least red AND green
id<=[COLORS]                                # color identity for Commander
id<=g                                       # within green identity
```

### Mana Cost
```
cmc=3    cmc<=2    cmc>=5
mana:{2}{U}    mana:{X}{R}{R}
```

### Oracle Text
```
o:"draw a card"         # exact phrase in rules text
o:"when ~ enters"       # ~ = the card's own name
```

### Format Legality
```
f:standard  f:pioneer  f:modern  f:legacy  f:commander  f:pauper
banned:commander
```

### Price & Rarity
```
usd<=1.00    usd>=10    usd<=0.25
r:common  r:uncommon  r:rare  r:mythic
```

### Sorting
```
order:edhrec      # Commander popularity (most useful for EDH)
order:cmc         # By mana cost
order:price       # By price
dir:asc / dir:desc
```

### Boolean
```
# AND — implicit, just combine terms
t:creature c:g cmc<=3

# OR — use "or"
t:instant or t:sorcery

# NOT — use "-"
t:creature -t:legendary

# Grouping
(t:forest or t:mountain) t:basic
```

### Useful Templates
```
# All cards for a Commander strategy
id<=[COLORS] f:commander o:"[KEY EFFECT]" order:edhrec

# Budget replacement for an expensive card
o:"[EFFECT]" f:commander usd<=[BUDGET] -name:"[CARD TO REPLACE]"

# Find draw spells at a specific CMC
(t:instant or t:sorcery) o:"draw" c:[COLOR] cmc=[CMC] f:commander

# Fetchable dual lands
t:land (t:forest or t:island)
```

### Pro Tips
- `is:commander` — finds cards that can be commanders
- `is:permanent` — excludes instants and sorceries
- `is:spell` — excludes lands

---

## Evaluating New Sets

When a new set releases and you want to know if anything upgrades an existing deck:

1. **Web Search:** `"[Commander name] [Set Name] upgrades"` or `"[Set Name] Commander staples"`
2. **EDHREC:** Look up the commander and check the "New Cards" tab
3. **Scryfall:** `e:[SET CODE] id<=[COLORS] f:commander order:edhrec`

**Rate test each standout card:**
- Is the rate competitive vs. existing cards at the same CMC?
- Does it do something the deck currently can't?
- Is it the best card at this function, or a slightly worse version of something that exists?

**Mechanics to know for Scryfall searches:**

| Mechanic | Search |
|----------|--------|
| Convoke | `o:convoke` |
| Delve | `o:delve` |
| Escape | `o:escape` |
| Flashback | `o:flashback` |
| Proliferate | `o:proliferate` |
| Cascade | `o:cascade` |
| Kicker | `o:kicker` |

---

## Edge Cases

### "I don't know what mechanic I need"
If the user describes a feeling rather than a mechanic, help identify it:
- "Mess with their mana" → Winter Orb, Tangle Wire, Blood Moon, Spreading Seas
- "Screw with their hand" → Thoughtseize, Inquisition of Kozilek, Duress, Hymn to Tourach
- "Stop their creatures" → Fog effects, rattlesnake creatures, pillow fort enchantments

### "I want budget alternatives to [Expensive Card]"
```
o:"[key effect text]" f:commander usd<=[budget] -name:"[card to replace]" order:edhrec
```

### "Does a card exist that does X AND Y?"
Use compound oracle text queries:
```
o:"[effect 1]" o:"[effect 2]" f:commander
```
If nothing does both, present two separate options and note the tradeoff.

---

## Output Format

```markdown
## Card Search: [Description of Need]
**For:** [Deck / Commander]
**Query:** [Scryfall syntax used]

### Top Results

1. **[Card Name]** — {Mana Cost}
   Effect: [1-line]
   Why it fits: [specific reason for this deck]
   Price: $X.XX

2. **[Card Name]** — {Mana Cost}
   ...

**Best fit:** [Card] — [1-2 sentence justification]
**Budget pick:** [Card] — [if applicable]
```
