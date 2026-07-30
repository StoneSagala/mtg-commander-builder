# Magic the Gathering — Deck Builder

An agent-native workspace for building, researching, and optimizing Commander decks. Three siloed workspaces — each handling one phase. An agent drops into a workspace, reads its CONTEXT.md, does its work, and exits.

**Persona and tone:** Read [`_shared/voice.md`](_shared/voice.md) before talking to a player.

---

## Starting Every Conversation

Figure out which path the player wants — it's usually clear from their first message:

> "Are we building something new, or do you have a deck you want to work on?"

**Building new** → Go to Ideation. Have the conversation naturally — don't mention the intake script.

**Have a deck** → Ask for the deck *before* anything else. Don't ask what's wrong with it. Get the deck, run diagnostics, share what you found. Don't ask open-ended questions when the numbers already tell you what needs work.

> "Nice, drop it here! Paste the list, share the file, or send me a Moxfield or Archidekt link — whatever's easiest."

---

## Quick Navigation

| Want to…                                 | Go here                                             |
| ---------------------------------------- | --------------------------------------------------- |
| **Start a new Commander deck**           | `Ideation/CONTEXT.md` → skill `/ideate`             |
| **Build a deck from a brief**            | `deckbuilding/CONTEXT.md` → skill `/brew-commander` |
| **Look up format rules / ban lists**     | `deckbuilding/docs/formats.md`                      |
| **Understand an archetype**              | `deckbuilding/docs/archetypes.md`                   |
| **Find cards for a synergy or function** | skill `/card-search`                                |
| **Fix my mana base**                     | `optimization/CONTEXT.md` → skill `/mana-base`      |
| **Tune an existing deck**                | `optimization/CONTEXT.md` → skill `/tune-deck`      |
| **Check the meta**                       | `optimization/CONTEXT.md` → skill `/meta-check`     |

Full workspace map → `CONTEXT.md`

**DO NOT ENTER:** `frontend/` and `backend/` are the web app codebase — no deck-building work happens there.

---

## Cross-Workspace Flow

```
Ideation/ → creates deckbuilding/brews/[slug]-draft.md
    ↓
deckbuilding/ → brews/[slug]-review.md → decklists/[slug]-final.md
    ↓
optimization/ → sessions/[deck]-[YYYY-MM-DD].md → decklists/[slug]-final.md

[Existing deck] → optimization/ directly (paste / file path / URL)
```

Flow is one-way. Load only the workspace you're in.

---

## Naming & Placement

| Content Type         | Pattern                  | Location                        |
| -------------------- | ------------------------ | ------------------------------- |
| Brew (WIP)           | `[slug]-[status].md`     | `deckbuilding/brews/`           |
| Finalized deck       | `[slug]-final.md`        | `deckbuilding/decklists/`       |
| Optimization session | `[deck]-[YYYY-MM-DD].md` | `optimization/sessions/`        |
| Deck primer/guide    | `[slug]-primer.md`       | `deckbuilding/docs/`            |

**Statuses:** `draft` → `review` → `final`

---

## Token Management

Each workspace is siloed. Load only what the current task needs. Each workspace's CONTEXT.md specifies exact load/skip rules — trust them over this file.
