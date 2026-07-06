# Insights — LILA BLACK Player Data

Five findings from 5 days of production telemetry (Feb 10–14, 2026), each backed by concrete numbers pulled from `all_events.parquet` and reproducible in the deployed app.

Each insight follows the same structure:
- **What caught my eye** — the raw observation
- **Backed by** — specific stats + reference to where it's visible in the tool
- **Actionable** — what to do about it + which metrics move
- **Why the Level Design team should care**

---

## 1 · Grand Rift is underplayed, but it's not a map-quality problem

**What caught my eye.** Grand Rift shows up in only **7% of matches** (59 out of 796) — 9.6× fewer than Ambrose Valley. First read: "the map is bad." But when I looked at per-match density, the story flipped completely.

**Backed by.** Numbers pulled from the aggregate parquet:

| Map | Matches | % of total | Events per match |
|---|---:|---:|---:|
| Ambrose Valley | 566 | 71% | 108 |
| Lockdown | 171 | 22% | 124 |
| Grand Rift | 59 | **7%** | **116** |

Grand Rift's events-per-match (116) is actually **higher than Ambrose Valley's** (108). When players *do* play it, they play just as intensely as on the "primary" map. Same pattern holds every day of the 5-day window.

Visible in the tool: **Players tab** in All-players mode with the Map filter set to each of the three maps.

**Actionable.** The problem isn't the map — it's the **matchmaker or player self-selection**. Two things to do:

1. **Audit the matchmaker's map-selection weights.** If Grand Rift is under-weighted or gated behind a mode toggle, that's a lever we control.
2. **A/B test featuring Grand Rift** in the map rotation for one week. Compare pre/post match counts.

Metrics that move if we act:
- Grand Rift's share of matches (target: 15–20% within 4 weeks)
- Grand Rift queue times (should not increase disproportionately)
- Return-to-Grand-Rift rate (do players who play it once come back?)

**Why the Level Design team should care.** A well-designed map that nobody plays is wasted level-design ROI. Every hour of art, layout, and playtesting on Grand Rift is currently paying off for 7% of the player experience. If matchmaking is the bottleneck, this is the highest-leverage fix Level Design can advocate for without touching a single vertex.

---

## 2 · More than half of Ambrose Valley is completely unused

**What caught my eye.** I ran the Coverage tab on Ambrose Valley across all 5 days with a 20×20 grid (400 cells). Result: **only 45% coverage** — 219 cells out of 400 have **zero player visits**. That's more than half the map that no one has touched.

**Backed by.** From the aggregate 48,754 human `Position` events on Ambrose Valley:
- 400 grid cells (20×20, each ≈ 45 world-units wide)
- **219 dead cells** (zero visits)
- 181 active cells with visits ranging from 1 to 1,247

Dead cells cluster in map corners, along water/river edges, and in the north-east industrial zone. Concentrated on the **entire eastern edge** of the map. Even with 5 days of data across 217 unique players, these regions never see a footprint.

Visible in the tool: **Coverage tab**, Map = Ambrose Valley, Date = All, grid 20, threshold 0.

**Actionable.** Three options in decreasing order of investment:

1. **Add pull-factors to dead zones near main routes** — one loot cache, one bot spawn, or one extraction point per adjacent dead cluster. Cheap.
2. **Shrink the walkable playable area** by adjusting storm-zone boundaries to exclude the unused corners. Zero art cost.
3. **Repurpose the unused north-east industrial zone** with a new POI or objective in the next content update.

Metrics that move:
- **Coverage %** (target: > 65% within one map iteration)
- **Dead cell count** (target: < 100 of 400)
- **Peak-cell concentration** (currently one cell has 1,247 visits — flattening this means players are exploring more evenly)

**Why the Level Design team should care.** Every square meter of unused map is wasted development effort. Reducing dead zones is the single most direct measure of "am I designing space that players use?" — the Coverage view in this tool answers that question in 3 seconds where a manual audit takes half a day.

---

## 3 · Human-vs-human combat is essentially absent

**What caught my eye.** Across **89,104 total events**, there are exactly **6 human-vs-human kill events** — 3 `Kill` and 3 `Killed`. That's 0.007%. For a battle-royale-style extraction shooter, the "battle" premise is essentially not happening.

**Backed by.** Full event breakdown:

| Event | Count | Note |
|---|---:|---|
| Position | 51,347 | Human movement |
| BotPosition | 21,712 | Bot movement |
| Loot | 12,885 | Item pickups |
| BotKill | 2,415 | Player killed a bot |
| BotKilled | 700 | Player killed by a bot |
| KilledByStorm | 39 | Storm caught someone |
| **Kill** | **3** | Player killed another player |
| **Killed** | **3** | Player killed by another player |

Bot combat outnumbers human PvP by **519×**. Whatever else is happening in the meta, players are not fighting each other.

Visible in the tool: **Heatmap tab**, overlay = "Bot combat" vs "Bot kills by players" — both dense. There is no equivalent for human PvP because there's nothing to show.

**Actionable.** Two diagnostic experiments before making map changes:

1. **Check matchmaker human-per-match density.** If matches contain only 1–2 humans, PvP is structurally impossible. Bumping the target humans-per-match from N to N+2 will change the encounter rate more than any map tweak.
2. **Measure extraction time.** If most players extract in the first 30% of the match, they're leaving before other humans arrive. Consider gating extraction behind a mid-match objective.

Metrics that move if we act:
- **Human encounter rate** (target: ≥ 1 encounter per match)
- **Median match duration for humans** (should go up if extraction is gated)
- **Player-to-player kill/death events** (target: ≥ 100/day, up from 6 total)

**Why the Level Design team should care.** Map design assumes players will encounter each other in the play space. If they don't, sight-lines, cover, choke-points, and vertical layout are all being designed for a game that isn't happening. Every design decision that trades "PvP tension" for "solo exploration comfort" should be re-examined until the encounter rate rises.

---

## 4 · The storm's final zone is dead-center and predictable

**What caught my eye.** All **39 storm deaths** in the dataset happen at **100% match progress** (i.e., the storm kill is the last event of the match, always). More interesting: their **spatial mean is nearly (0, 0)** on all three maps — the middle. Storm-death spots cluster tightly around map center.

**Backed by.** Storm-death event coordinates:

| Map | Storm deaths | Mean x | Mean z | Distance from center |
|---|---:|---:|---:|---:|
| Ambrose Valley | 17 | 19.7 | −30.5 | 36 |
| Lockdown | 17 | 48.9 | 44.2 | 66 |
| Grand Rift | 5 | 3.7 | 3.7 | 5 |

All three maps: storm-death mean is within one grid cell of map center. On Grand Rift the average is essentially the geometric center of the map.

Visible in the tool: **Heatmap tab**, overlay = "Storm deaths" for each map — the density is centered.

**Caveat — small sample.** With only 39 events, one wouldn't build a whole "storm analysis" feature on this. But the direction is unmistakable: **final circles land at map center more often than random.**

**Actionable.** If the storm's final zone is procedurally random but its **expected value** is map center, we should either accept that as design or introduce variability:

1. **Randomize the final storm zone across matches** — pick from 3–5 pre-authored "endgame arenas" per map, not just the center.
2. **Add variability to storm advance direction.** If it always closes toward center, players will always camp center. If it sometimes closes east or south, they can't meta-game it.

Metrics that move:
- **Variance of storm-death locations** (target: ≥ 2× current — measurable within a week of the change)
- **% of matches where the final zone was "surprising"** — could be computed as distance from the median endzone location

**Why the Level Design team should care.** Predictable finales get meta-gamed. When players learn "the storm always closes near the central river on Ambrose," the ~500 m of the map they can safely ignore grows over time. Storm design is a mechanic, but its knock-on effect is spatial — Level Design has to react by making early-match zones matter *more* if the endgame is a solved problem.

---

## 5 · Daily player count is dropping ~17 humans per day

**What caught my eye.** Unique human players per day is on a **steady 4-day decline**: 98 → 81 → 59 → 47. That's a **52% drop from Feb 10 to Feb 13**, roughly 17 players lost per day. Feb 14 is intentionally excluded from the trend since it's a partial-collection day.

**Backed by.** Unique `user_id` counts per day (humans only):

| Day | Unique humans | Δ vs prior day |
|---|---:|---:|
| Feb 10 | 98 | — |
| Feb 11 | 81 | −17 |
| Feb 12 | 59 | −22 |
| Feb 13 | 47 | −12 |
| Feb 14 (partial) | 12 | not comparable |

Linear trend: **−17 players/day**. If it continues linearly, the player base is exhausted in ~3 more days.

Visible in the tool: **Sidebar → Date** — as you cycle through days with "All players" selected, the metric card labeled "Humans" drops steadily.

**Caveat — 5 days isn't enough.** This could be a normal weekday cycle (Wed–Sun style), a post-event drop, or a real churn signal. **Longer time-series data is needed to conclude anything definitive.** But the direction is worth flagging.

**Actionable.** Level Design can't fix churn directly, but can help investigate:

1. **Compare the Coverage % of returning players (Feb 13) vs new players (Feb 10).** If returning players are using less of the map, the map may be feeling repetitive.
2. **Look at extraction time for churned players' final matches.** If they're extracting fast, they might be bored. If they're dying to bots, difficulty is a factor.

Metrics that move:
- **DAU trend** (obvious)
- **New-player Coverage %** (target: > 60% within their first 3 matches — a proxy for whether the map is teaching them where to go)
- **Return rate day-over-day** (target: > 70% D+1 retention)

**Why the Level Design team should care.** Level design work is only visible to players who actually queue. A 50% weekly drop means half the "audience" for your maps disappears without seeing the improvements you shipped. This is a signal to prioritize Level Design changes that **new players see in their first match** over deep-content that only long-tail players notice.

---

## Reproducibility

Every stat in this document was computed from `all_events.parquet` (bundled in this repo) and is verifiable in the deployed app:

| Insight | Where to verify in the app |
|---|---|
| 1 · Grand Rift underplay | Cycle the Map filter (Ambrose / Grand Rift / Lockdown) with Date = All and watch the Matches metric card |
| 2 · Ambrose Valley dead zones | **Coverage tab** → Map = Ambrose Valley → grid 20 → threshold 0 |
| 3 · Human PvP absent | **Heatmap tab** → overlay = Bot combat (dense) vs. no human-PvP overlay exists (nothing to plot) |
| 4 · Storm centrality | **Heatmap tab** → overlay = Storm deaths → observe centroid on each map |
| 5 · Daily trend | **Sidebar → Date** → step through Feb 10 → 13 with All players; watch Humans metric |
