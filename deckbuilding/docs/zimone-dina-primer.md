# Zimone and Dina — Sultai Lands Primer

> Historical deck-specific primer. Revalidate cards, prices, bans and bracket expectations before using it; current rule references are generated separately.

*Bracket 4 | "The lands are the superstars"*

---

# Part 1: What This Deck Is

This is a lands engine deck. Every land you play does something beyond making mana — it creates a zombie, drains an opponent, draws you a card, or generates extra mana. Zimone and Dina sits at the center converting zombies into cards and land drops, the untap package runs the engine on everyone's turn, and Glacial Chasm makes you untouchable while it all happens.

**Read the commander carefully, because every line matters:**

> **Zimone and Dina** {B}{G}{U} — 3/4
> Whenever you draw your **second card each turn**, target opponent loses 2 life and you gain 2 life.
> {T}, Sacrifice another creature: Draw a card. You may put a land card from your hand onto the battlefield tapped. **If you control eight or more lands, repeat this process once.**

Three things people miss on first read:

1. **"Each turn" means every turn — including opponents' turns.** If you draw two cards on each opponent's turn (easy with instant-speed activations), the drain fires four times per turn cycle, not once. That's 8 damage spread around and 8 life gained per full rotation, from the commander alone.
2. **The 8-land repeat doubles everything.** One activation at 8+ lands = draw 2 (drain trigger guaranteed), put 2 lands into play (2 landfall triggers, 2 zombies with Field of the Dead). The deck hits 8 lands around turn 5–6 without trying.
3. **She drops the land tapped, but landfall doesn't care.** Every landfall payoff still triggers.

The engine in one sentence: **Field of the Dead turns lands into zombies, Zimone and Dina turns zombies back into lands and cards, and every cycle through that loop drains the table.**

---

# Part 2: The Combos — In Depth

## Combo 1: The Coralhelm Loop (infinite landfall)

**Pieces:** Retreat to Coralhelm + Sakura-Tribe Scout + any karoo land in hand (Simic Growth Chamber, Dimir Aqueduct, Golgari Rot Farm, or Guildless Commons)

**Setup cost:** Retreat is {2}{U}, Scout is {G} and needs to have been out since your last turn. The loop itself costs **zero mana**.

**The exact loop:**
1. Tap Sakura-Tribe Scout: put Simic Growth Chamber from your hand onto the battlefield.
2. Growth Chamber entering is a landfall event → **Retreat to Coralhelm triggers** → choose "untap target creature" → untap Scout.
3. Growth Chamber's own trigger resolves: "return a land you control to its hand" — **it can return itself.** Growth Chamber goes back to your hand.
4. You're back exactly where you started: Scout untapped, karoo in hand. Repeat for as many landfall triggers as you want.

**Why this is legal and clean:** each iteration is a full loop of real game actions, no mana involved, no card disadvantage. You announce the loop, demonstrate one iteration, declare a number (e.g., "five million landfall triggers"), and point at your payoff.

**What converts the triggers into a win:**
| Payoff on board | Result |
|---|---|
| Ob Nixilis, the Fallen | Infinite damage — 3 per trigger, aimed anywhere. Table dies on the spot. |
| Field of the Dead (7+ names) | Infinite 2/2 zombies. Wins next combat, or instantly with Zulaport Cutthroat out (each one entering doesn't drain — but sacking them all to Zimone and Dina later does; with Zulaport you usually want the Ob Nix line instead). |
| Lotus Cobra / Tireless Provisioner | Infinite mana (Cobra) or treasures (Provisioner) → cast **Torment of Hailfire** for X = a billion. |
| Tatyova / Aesi | Draw your entire deck → find Ob Nixilis or Torment → win from there. (Stop drawing before you deck yourself!) |
| Retreat to Hagra (instead of Coralhelm payoff) | Note: Hagra can't sustain the loop itself — Coralhelm does the untapping — but if both Retreats are out, every iteration also drains 1. Infinite drain. |

**Backup pilots for the loop:**
- **Kiora's Follower** can replace Scout, but the loop changes: Follower doesn't put lands into play, it *untaps* things. The variant needs **Amulet of Vigor** + a karoo on the battlefield: tap karoo for 2 mana, it returns a land (itself) — no wait, karoos only bounce on entry. The real Follower variant: you play the karoo with your land drop or Scout, and Follower + Retreat untap each other for mana. Treat Follower as a value piece and a **redundant untapper**, not a true second copy of Scout.
- **Springheart Nantuko bestowed on something** turns every loop iteration into a 1/1 snake instead — slower than Ob Nix but still infinite bodies.

**How it dies, and your answers:**
- Removal on Scout in response to the Retreat trigger → loop fizzles. Hold **Heroic Intervention / Veil of Summer** when you go for it.
- Enchantment removal on Retreat → same answer.
- **Cursed Totem effects** shut Scout off entirely → Assassin's Trophy / Beast Within on sight, before you attempt the loop.

**How to assemble it:** Green Sun's Zenith finds Scout (X=1). Retreat to Coralhelm has no tutor in the deck except Demonic Tutor — if you're holding Demonic and the table is shields-down, Retreat is usually the get. The karoo is the easy part: **Elvish Reclaimer or any land tutor** fetches one.

---

## Combo 2: Thespian's Stage + Dark Depths (Marit Lage)

**Pieces:** Both lands on the battlefield. Thespian's Stage needs {2} to activate.

**The exact sequence — this order matters:**
1. Activate Thespian's Stage: {2}, tap Stage → Stage becomes a copy of Dark Depths.
2. **Copy effects don't copy counters.** The Stage-Depths enters... well, it doesn't "enter" — it just *becomes* Dark Depths with **zero ice counters** on it.
3. Legend rule check: you control two Dark Depths. **You choose which to keep — keep the copy** (the one with no counters), put the original in the graveyard.
4. The surviving Dark Depths has no ice counters → its trigger condition is met: "When Dark Depths has no ice counters on it, sacrifice it. If you do, create Marit Lage."
5. **20/20 flying indestructible black Avatar token.** Total cost: {2} and two land drops you'd have made anyway.

**Do it at instant speed.** Stage's ability is an activated ability — activate it on an opponent's end step, untap with a 20/20 and full mana. Or in response to a board wipe (Marit Lage is indestructible — most wipes miss entirely; only exile/-X/X effects and Toxic Deluge-style effects get her).

**Kill math:** 20 commander-free damage. At 40 life that's exactly two swings per player. With the table already drained to ≤20 by your engine, it's one.

**Assembly:** This is the most tutorable win in the deck —
- **Hour of Promise** gets *both pieces at once* (any two lands, tapped — set up the turn before, activate next turn or EOT).
- **Crop Rotation** (instant!), **Elvish Reclaimer** (repeatable!), **Sylvan Scrying**, **Expedition Map**, **Ulvenwald Hydra**, **Tempt with Discovery**, and **Tolaria West** (transmute finds any 0-cost card — both pieces qualify) each get the missing half.
- **Vesuva** can copy Dark Depths — but careful: Vesuva enters *as* Depths and enters **with** the counters (it's an ETB copy, counters are part of how Depths enters). Vesuva is NOT a Stage substitute for this combo. Vesuva's best target is Field of the Dead.

**How it dies:** Swords/Path don't exist in most Sultai pods, but exile removal, bounce (Cyclonic Rift), and sacrifice edicts all answer Marit Lage. Don't tap out to make her into open blue mana if she's your only line — or hold Swan Song.

---

## Combo 3: Thornbite Staff + Zimone and Dina + Field of the Dead (the machine gun)

**Pieces:** Thornbite Staff equipped to Zimone and Dina ({4} to equip, do it on an empty turn), Field of the Dead online (7+ land names), 8+ lands, some lands in hand, one creature to start.

**The chain:**
1. Tap Zimone and Dina, sac a zombie: draw 2 cards, put 2 lands from hand into play (8+ lands).
2. The sacked zombie **died** → Thornbite Staff triggers → **untap Zimone and Dina.**
3. The 2 lands entering → Field of the Dead triggers twice → **2 new zombies.**
4. You now have: an untapped commander, more fodder than you started with, and 2 fresh cards. Go back to step 1.

**Each iteration nets:** +2 cards drawn, +2 lands on battlefield, +1 zombie (made 2, sacked 1), and your second draw drained someone for 2. The chain runs until you're out of lands in hand — and you're drawing 2 per iteration, so it frequently sustains itself for 4–8 iterations per turn. With **Zulaport Cutthroat** out, every sacked zombie drains the whole table for 1 more.

This isn't technically infinite — it's bounded by lands drawn — but in practice it's "I drained the table for 12 and made six zombies, go."

**Same chain, different untapper:** **Intruder Alarm** does the Staff's job differently — every creature entering (each zombie!) untaps ALL your creatures, including the commander. Strictly more explosive, but warning: it untaps opponents' creatures too. Read the table before deploying.

---

## Combo 4: Bloodghast — the immortal fodder

Not a combo so much as a cheat code: sac Bloodghast to Zimone and Dina → the activation itself puts a land into play → **landfall returns Bloodghast from the graveyard.** Your sac outlet's cost refunds itself every single activation. If you ever see Bloodghast early, it's one of the best keeps in the deck — it means the commander never lacks fodder.

(Skullclamp note: Bloodghast wearing Skullclamp dies to the +1/-1, draws 2, returns on your next land. That's 2 cards per land drop, plus the drain trigger. Filthy.)

---

## Combo 5: The Glacial Chasm lock (soft lock, hard to break)

> **Glacial Chasm:** Cumulative upkeep — pay 2 life. When it enters, sacrifice a land. Creatures can't attack you.

**Why the drawbacks don't hurt you:**
- *Sac a land on entry:* sac a spent fetch, or a karoo you wanted to replay, or literally any land — Crucible replays it.
- *Cumulative upkeep:* 2, then 4, then 6 life per turn... but Zimone and Dina gains you 2+ per turn cycle, and the engine gains more with Zulaport. You can run the Chasm for 4–6 turns before the math gets uncomfortable.

**The reset trick (this is the whole point):** when the upkeep gets too expensive, **don't pay** — Chasm goes to the graveyard. Then replay it from the graveyard with **Crucible of Worlds / Ramunap Excavator / Ancient Greenwarden** as your land drop. It's a new object: **age counters gone, cumulative upkeep restarts at 2.** Life from the Loam can also dredge it back to hand. Between those four cards, you can keep the lock up *for the rest of the game*, paying an average of ~3 life a turn while your commander gains it back.

**Ghost Town synergy:** Ghost Town returns itself to your hand during opponents' upkeeps — so the Chasm "sacrifice a land" cost can effectively eat Ghost Town over and over too.

**What the lock does NOT stop:** non-combat damage, combo wins, Torment of Hailfire pointed at you. The Chasm buys you immunity from the aggro decks; your counterspells handle the combo decks. Know which threat you're holding answers for.

---

## Combo 6: Scapeshift (the one-card army)

Sacrifice X lands, search up X lands with **different names**, all entering at once. The play pattern at 8+ lands:

- Sac 7, fetch **Field of the Dead + 6 new names.** Every one of those lands entering triggers Field (the trigger checks the 7-name condition as they resolve, and they all see each other) → **~7 zombies immediately**, plus you just fixed every color and stocked the graveyard for Crucible.
- Already have Field out? Fetch **Dark Depths + Thespian's Stage + Glacial Chasm + Bojuka Bog + utility** — assemble Marit Lage, the lock, and graveyard hate in one card, while making 7 more zombies.

Scapeshift is arguably the strongest single card in the 99. Tutor priority when you're ahead.

---

# Part 3: Win Conditions — How Each One Actually Closes

Listed by how often they'll win you real games.

### Win Con 1: The Drain Engine (≈half your wins)
No single big turn — the table just bleeds. The sources stack:
- **Commander:** 2 per turn she fires, every turn including opponents' (with untappers). 4 firings/cycle = 8 drain.
- **Zulaport Cutthroat:** 1 to *everyone* per creature you sac. Six activations a turn = 18 total damage across the table.
- **Retreat to Hagra:** 1 drain per landfall. You average 3–6 landfall events a turn.

Realistic mid-game turn cycle: 10–15 total drain spread across opponents, while you gain 6–10. Starting around turn 6–7, opponents have ~10 turns to live, and it accelerates every turn. **Seedborn Muse is what turns this from "win by turn 15" into "win by turn 9"** — she quadruples your activation rate.

### Win Con 2: Ob Nixilis, the Fallen (the burn plan)
Landfall: **target opponent loses 3 — and he grows +1/+1 each time.** You make 3–6 land drops a turn (commander activations, fetches, Harrow, extra drops). That's 9–18 damage a turn, *aimed* — you can execute the player closest to comboing. Two dedicated turns kill a player from 40. He's also your answer to lifegain decks: point everything at them.

### Win Con 3: The Coralhelm Loop (the "we're done here" button)
Detailed in Part 2. This is your actual combo finish — when the table is taking too long or someone else is about to win, assemble and end it. Bracket 4 pods expect this; demonstrate cleanly.

### Win Con 4: Marit Lage (the surprise wall-breaker)
20/20 flying indestructible at instant speed for {2}. Best when: the table is drained low (one swing kills), someone wiped the board (she survives), or you need a blocker that ends an attacker's whole career. Two pieces, five tutors that find them.

### Win Con 5: Torment of Hailfire (the cleanup)
X = mana you have. Lotus Cobra + Tireless Provisioner turns mean 8–15 mana turns are normal late; X=10 against three opponents who've each been drained to 15–20 is lethal-or-devastating. Each mode they choose hurts: lose the permanents they kept, discard the answers they held, or take the damage. After a board wipe resets everyone else, this closes alone. With infinite mana from the loop it's just the kill text.

### The zombies themselves (honorable mention)
Don't forget Field of the Dead tokens are a clock all by themselves. Eight 2/2s swinging at the player without blockers is 16 a turn. Scute Swarm doubles per landfall once it gets going and gets unreasonable within two turns. You're not an aggro deck, but sometimes the door is just open.

---

# Part 4: Strategy — How to Pilot Each Phase

## Turns 1–3: Develop greedily, look harmless
- Priorities in order: land drop every turn (obviously) → **Burgeoning/Exploration/Arboreal Grazer on turn 1** (Burgeoning is the single most explosive turn-1 play: you drop a land on each opponent's turn too) → 1–2 CMC ramp (Sakura-Tribe Elder, Farseek, Nature's Lore, Three Visits) → Azusa.
- **Elvish Reclaimer turn 1** is the other premium opener — from turn 2 on, it converts any land into Field of the Dead, Glacial Chasm, or a combo piece, every single turn.
- **Crack fetches for names, not just colors.** Field of the Dead counts *different names* — fetch Snow-Covered Island when you already have Island. Every name matters.
- Cast Zimone and Dina turn 3 if the table is calm. She's rarely a removal magnet this early, and her draw engine compounds. Sakura-Tribe Elder is her first sac snack (you were sacking it anyway).
- **Don't lead with Storm Cauldron or Intruder Alarm** — symmetric pieces wait until YOUR side of the symmetry is set up.

## Turns 4–6: Engine online, shields up
- Field of the Dead goes online around here (7 names is automatic with this mana base). From this point every land is a body.
- **Sequencing rule: lands before activations.** Play your land drop(s) first, THEN tap the commander — so the lands she puts in benefit from full landfall counts and her 8-land check.
- **Seedborn Muse timing:** she eats removal within one turn cycle, almost guaranteed. Land her when you can hold Heroic Intervention up, or when an opponent just tapped out. Even one full rotation of her is usually worth 6+ drain and 4+ cards.
- Get **Glacial Chasm** down the moment any board looks scary — don't wait to be attacked first. Crop Rotation at instant speed (in response to attacks, even) is the rescue move.
- Hold one counterspell from here on. Its job is protecting **your engine** (Field of the Dead, Crucible, the commander on a big turn) or stopping **their win**, nothing else. Counterspell-as-tempo is a trap in this deck.

## Turns 7+: Pick a lane and close
By now you're drawing 4–6 cards a turn and draining on autopilot. Assess:
- **Table is slow / durdling:** assemble the Coralhelm loop or Thornbite chain. Tutors → Demonic for Retreat, GSZ for Scout.
- **Someone's about to win:** counterspell their attempt, then close FAST next rotation — Ob Nixilis + multiple land drops, or instant-speed Marit Lage and swing.
- **You're the archenemy and they're coming:** Chasm up, drain through it. They literally cannot attack you; every turn they spend wide open is a turn you gain on them.
- **Protection discipline:** Heroic Intervention, Veil of Summer, and Fierce Guardianship are FOR THE WIN TURN. Don't spend them saving a Lotus Cobra. The most common way this deck loses is spending its protection on value and going for the win naked.

## Threat assessment — remove ON SIGHT:
1. **Blood Moon / Back to Basics / Magus of the Moon** — you run 29 nonbasics; this is death. Trophy/Beast Within immediately, even on an empty board.
2. **Cursed Totem / Linvala / Collector Ouphe (for Staff lines)** — turns off the commander AND Scout.
3. **Rest in Peace / Leyline of the Void** — kills Bloodghast, Loam, the Chasm reset, Crucible. The engine survives but the lock doesn't.
4. **Torpor Orb-style effects** — Field of the Dead is a triggered ability of a land (safe), but Ancient Greenwarden, Tatyova, Lotus Cobra all suffer. Annoying, not fatal.

---

# Part 5: Opening Hands — Real Examples

**The rule:** keep 2–4 lands + at least one *engine piece* (extra land drops, landfall payoff, recursion, or cheap ramp). Ship hands that are all payoff or all mana.

### Hand 1 — KEEP (the dream)
`Misty Rainforest, Forest, Simic Growth Chamber, Exploration, Lotus Cobra, Crop Rotation, Counterspell`
Turn 1 Exploration off Forest. Turn 2: Cobra + double land drop = mana jumping immediately. Crop Rotation converts any land into Field of the Dead later. A counterspell to protect it. This hand wins games.

### Hand 2 — KEEP (slower, but real)
`Swamp, Island, Golgari Rot Farm, Sakura-Tribe Elder, Zimone and Dina (you know she's castable T3), Skullclamp, Beast Within`
Ramp into commander on curve, Elder is her first meal, Skullclamp converts future zombies into gas. Interaction for emergencies. Nothing flashy, everything functional.

### Hand 3 — KEEP (the greedy keep that's actually fine)
`Verdant Catacombs, Khalni Garden, Azusa, Life from the Loam, Field of the Dead, Bloodghast, Ob Nixilis the Fallen`
Two lands but one is a fetch and you have **Loam** — you will not miss drops; Loam + fetch is a draw engine all by itself. Azusa accelerates everything, and the top end is your actual win con. The kind of hand that looks risky and plays out beautifully.

### Hand 4 — SHIP (all gas, no engine)
`Island, Torment of Hailfire, Seedborn Muse, Tatyova, Retreat to Coralhelm, Demonic Tutor, Counterspell`
One land, nothing castable before turn 3, and every card wants a developed board that doesn't exist. Even Demonic Tutor can't fix one land. Mulligan, no hesitation.

### Hand 5 — SHIP (the trap)
`Forest, Island, Swamp, Command Tower, Glacial Chasm, Vesuva, Counterspell`
Six lands and a counterspell. "But it's a lands deck!" — no. There's no *engine*: nothing converts these lands into cards or bodies. You'll draw one card a turn off the top all game. Ship it.

### Hand 6 — KEEP, with a plan
`Polluted Delta, Snow-Covered Swamp, Dimir Aqueduct, Farseek, Quirion Ranger, Tatyova, Heroic Intervention`
Three lands (3 different names + whatever Delta gets = 4 names by turn 2), early ramp, a draw engine on curve, an untapper, protection. Note the micro-synergy: Quirion Ranger bouncing a Forest... you have no Forest. She still untaps the commander later — fine, but know Farseek also can't fetch a Forest-type basic (it gets the OTHER types — grab a dual or shock... you run Breeding Pool/Overgrown Tomb/Zagoth Triome, all legal Farseek targets). Keep.

**Mulligan priorities at 6:** keep the lands-plus-engine core, bottom the most expensive card. A 6-card hand with Exploration in it plays like a 7.

---

# Part 6: Table Politics (Bracket 4, played friendly)

- **Turns 1–5 you look like a ramp deck.** "I'm just playing lands" is genuinely disarming. Don't explain what Field of the Dead is about to do; let them Google it.
- **Glacial Chasm redirects violence.** When the aggro player checks your Chasm and sighs, helpfully note who's open. You're not their enemy; you're a wall with a suggestion.
- **The moment Field of the Dead + Seedborn Muse are both visible, you are the archenemy.** That turn — that exact turn — is when your protection needs to be up. Plan the deployment order: protection mana available BEFORE the second engine piece lands.
- **Demonstrate loops cleanly.** One full iteration out loud, state the count, state the payoff, offer priority. "Does anyone have a response to the first trigger?" earns more goodwill than 40 minutes of physical zombie-token shuffling.
- **Ob Nixilis is targeted drain — use it politically.** Hitting the player who counterspelled you twice is justice everyone at the table understands.

---

# Quick Reference — The Decklist

**Commander:** Zimone and Dina

**Lands (38):** Command Tower · Field of the Dead · Thespian's Stage · Dark Depths · Glacial Chasm · Command Beacon · Boseiju, Who Endures · Otawara, Soaring City · Takenuma, Abandoned Mire · Bojuka Bog · Urborg, Tomb of Yawgmoth · Yavimaya, Cradle of Growth · Simic Growth Chamber · Dimir Aqueduct · Golgari Rot Farm · Guildless Commons · Ghost Town · Oboro, Palace in the Clouds · Dryad Arbor · Vesuva · Evolving Wilds · Tolaria West · Misty Rainforest · Verdant Catacombs · Polluted Delta · Khalni Garden · Zagoth Triome · Overgrown Tomb · Breeding Pool · Ancient Tomb · Forest ×2 · Island ×2 · Swamp ×2 · Snow-Covered Forest · Snow-Covered Swamp

**Ramp (9):** Sol Ring · Burgeoning · Arboreal Grazer · Sakura-Tribe Elder · Nature's Lore · Three Visits · Cultivate · Farseek · Harrow

**Extra Land Drops (6):** Exploration · Azusa, Lost but Seeking · Oracle of Mul Daya · Wayward Swordtooth · Dryad of the Ilysian Grove · Spelunking

**Card Draw (5):** Tatyova, Benthic Druid · Aesi, Tyrant of Gyre Strait · Sylvan Library · Skullclamp · Trade Routes

**Land Recursion (5):** Crucible of Worlds · Ramunap Excavator · Ancient Greenwarden · Life from the Loam · Eternal Witness

**Landfall Payoffs (5):** Lotus Cobra · Tireless Provisioner · Scute Swarm · Springheart Nantuko · Retreat to Hagra

**Untap Package (5):** Seedborn Muse · Kiora's Follower · Quirion Ranger · Intruder Alarm · Thornbite Staff

**Combo Pieces (4):** Retreat to Coralhelm · Sakura-Tribe Scout · Amulet of Vigor · Storm Cauldron

**Sac / Drain (2):** Bloodghast · Zulaport Cutthroat

**Win Conditions (2):** Ob Nixilis, the Fallen · Torment of Hailfire

**Tutors (10):** Elvish Reclaimer · Ulvenwald Hydra · Tempt with Discovery · Crop Rotation · Scapeshift · Hour of Promise · Sylvan Scrying · Expedition Map · Green Sun's Zenith · Demonic Tutor

**Interaction (8):** Counterspell · Swan Song · Fierce Guardianship · Heroic Intervention · Veil of Summer · Assassin's Trophy · Beast Within · Toxic Deluge
