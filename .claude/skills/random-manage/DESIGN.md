# random-manage Skill — Design

**Date**: 2026-04-22
**Status**: Approved for implementation planning
**Author**: niracler (with Claude as co-designer via brainstorming skill)

## 1. Context & Goal

The `niracler/random` repo runs a personal "monthly dare" system on top of
a GitHub Project (`PVT_kwHOAXsRh84Ak2d1`). Each project item is a GitHub
issue with fields `Status` (Backlog/Ready/Doing/Done/Reject) and `Priority`
(P0/P1/P2). Existing automation:

- `rand.py` — monthly random picker (moves a Ready item to Doing, posts to Telegram).
- `close_rejected.py` — batch-closes items with `Status=Reject`.

Day-to-day management (adding new ideas, listing items, changing status
or priority for a specific item) currently has no dedicated tool — it's
done through the GitHub web UI. This skill fills that gap.

## 2. Scope

### In (MVP, this skill)

1. **Create** a new random item from a natural-language request.
2. **List** items, with filters on status / priority / labels.
3. **Update Status** of a specific item.
4. **Update Priority** of a specific item (including clearing it).

### Out (deferred to a second skill: `random-review`)

- Monthly review against the 6 rules in `prompt.md`.
- Batch promotion from Backlog to Ready.
- Body / TODOList editing of existing items.
- Label editing (add / remove labels on existing items).

### Non-goals

- Cross-project reusability. This skill is hardcoded to
  `PVT_kwHOAXsRh84Ak2d1` and only activates inside `niracler/random`.
- Full schema discovery on every invocation. Project field / option IDs
  are treated as slow-changing constants and baked into the skill file.

## 3. Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Split into two skills; build `random-manage` first | Manage = infra (CRUD), Review = policy layer. Infra must exist first. |
| 2 | Implementation via `gh api graphql` + skill instructions (no Python scripts) | Single-user, single-machine use. Piggybacks on `gh` auth. Zero runtime deps. |
| 3 | Project Reference IDs hardcoded in SKILL.md with one-time discovery query | Schema changes rarely. Runtime discovery on every call is wasteful. |
| 4 | Keep `prompt.md` (do not delete during this skill's implementation) | Its 6 rules are `random-review` territory; its body-template sample is referenced by this skill's Mode C. |
| 5 | Create: natural-language input (Mode A) with mandatory preview/confirm; Mode C on explicit "draft a plan" request | Matches real capture-an-idea workflow while enforcing user review of AI-generated content. |
| 6 | Skill location: `repos/random/.claude/skills/random-manage/SKILL.md` | Skill is project-specific; co-locating it with the project (vs. global) scopes trigger correctly. |
| 7 | Default new-item `status = Backlog`, `priority = unset` | Aligns with Rule 1: "monthly review ready list" — new ideas park in Backlog until promoted. |
| 8 | Label whitelist: `practice`, `game`, `dare`, `research`, `portfolios`, `life_habit`. Skill must not invent new labels. | Keeps the taxonomy stable; new labels should be an explicit human decision, not AI drift. |
| 9 | Create transaction (4 mutations): no auto-rollback; report successful steps and stop on failure | Automated rollback on partial failure has worse failure modes (lost content) than honest reporting. |
| 10 | Single-file skill (no `references/` subfolder) | 4 operations, ~150 lines. Splitting adds navigation cost with no payoff at this scale. |
| 11 | Mode C body template references `../../../prompt.md` by relative path | Avoids duplication; if `prompt.md` changes or is removed during `random-review` work, this reference breaks loudly — that is the signal to update here. |
| 12 | List operation: show all matching rows; default to filtered view when >15 rows | Full dump is rarely useful; common usage is "what's in Ready" / "what's P0". |
| 13 | Item identification supports issue number (exact) and title substring (case-insensitive, fuzzy) | Low-friction voice patterns; disambiguation fallback for multiple matches. |

## 4. SKILL.md Outline

The skill is a single `SKILL.md` with six sections plus frontmatter.
Target length: 150–180 lines.

### 4.1 Frontmatter

```yaml
---
name: random-manage
description: Use this skill to manage items on niracler's personal "Random"
  GitHub Project (https://github.com/users/niracler/projects/1) — including
  creating new random-dare ideas, listing items by status/priority, updating
  an item's Status (Backlog/Ready/Doing/Done/Reject), or updating Priority
  (P0/P1/P2). Triggers on: "加一条 random/add to random/random 里加",
  "random 里有什么/show random list", "把 X 改成 Ready/Doing",
  "X 的优先级改成 P0". Only works in the niracler/random repository context.
---
```

### 4.2 Project Reference (§2)

Table of all opaque GraphQL IDs needed for mutations:

- `PROJECT_ID` = `PVT_kwHOAXsRh84Ak2d1` (known)
- `REPOSITORY_ID` — to discover
- `STATUS_FIELD_ID` = `PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o` (known)
- Status option IDs for Backlog / Ready / Doing (`47fc9ee4`) / Done / Reject
- `PRIORITY_FIELD_ID` — to discover
- Priority option IDs for P0 / P1 / P2
- Label IDs for the 6 whitelisted labels

Any value marked `TBD` blocks operations — the skill must run the
discovery query first (see §2.3 in SKILL.md).

**Discovery query (one-time bootstrap)**:

```bash
gh api graphql -f query='
query {
  node(id: "PVT_kwHOAXsRh84Ak2d1") {
    ... on ProjectV2 {
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id name
            options { id name }
          }
        }
      }
    }
  }
  repository(owner: "niracler", name: "random") {
    id
    labels(first: 30) { nodes { id name } }
  }
}'
```

User pastes the output, fills the table manually, commits. No
automatic rewrite of SKILL.md by the skill itself.

### 4.3 Operations

Four sub-sections, each with: trigger language examples, required
inputs, GraphQL template, confirmation format (for writes), and
error-handling callouts.

#### 4.3.1 Create Item

- **Trigger**: "加一条 random", "add to random", "random 里加 X", "帮我记一下：X" (and Mode C: "帮我 draft 计划 / 拆解 TODOList").
- **Input**: one sentence in natural language.
- **AI-generated** (Mode A): bilingual title (`"EN | 中文"`), bilingual
  summary, inferred labels from the whitelist.
- **Fixed defaults**: `status=Backlog`, `priority=unset`,
  `repository=niracler/random`.
- **Preview block** shown in chat before any mutation; user replies
  `yes` / `edit <field> <value>` / `cancel`.
- **4-step transaction** (all via `gh api graphql`):
  1. `createIssue(repositoryId, title, body, labelIds)` → `issueId`
  2. `addProjectV2ItemById(projectId, contentId=issueId)` → `projectItemId`
  3. `updateProjectV2ItemFieldValue` for Status = Backlog
  4. `updateProjectV2ItemFieldValue` for Priority (only if explicitly set)
- **Mode C**: identical flow; only difference is body is generated
  following `../../../prompt.md` bottom-half structure
  (`## Summary` / `## TODOList` with `### Step N:` / `### Books & Resources`).

#### 4.3.2 List Items

- **Trigger**: "show random list", "random 里有什么", "Ready 里有哪些", "P0 有哪些".
- **Query**: fetch up to 100 items with all fields and labels.
- **Filter**: client-side in Claude's response synthesis.
- **Output**: markdown table (`# | Title | Status | Priority | Labels`).
- **Default view**: filtered; full dump only when user says so.
- **No confirmation**: read-only.

#### 4.3.3 Update Status

- **Trigger**: "把 X 改成 Ready", "X 移到 Backlog", "close X" (→ Reject).
- **Identification algorithm** (shared with §4.3.4):
  1. Fetch current items (reuse List query).
  2. Match by issue number (exact) or title substring (case-insensitive).
  3. 0 matches → list candidates; 1 → proceed; >1 → disambiguate.
- **Confirmation**: `"即将把 [#42 Learning Tauri]  Status: Backlog → Ready, confirm?"`
- **Mutation**: `updateProjectV2ItemFieldValue` with `STATUS_FIELD_ID` + target option.
- **`itemId` is `projectItemId` (`PVTI_...`)**, not issue ID.

#### 4.3.4 Update Priority

- **Trigger**: "把 X 调成 P0", "X 降到 P2", "把 X 的 priority 清掉".
- **Same structure as §4.3.3**, with `PRIORITY_FIELD_ID`.
- **Clear priority** uses `clearProjectV2ItemFieldValue` mutation, not `update`.

### 4.4 Create Body Template

- **Mode A (minimal)**: `# title\n{EN | 中文}\n\n## Summary\n{EN | 中文}\n`.
- **Mode C (draft plan)**: full template from `../../../prompt.md` bottom half.
- **Title and Summary must use `"EN | 中文"`** separated by ` | ` —
  `rand.py` depends on this separator.

### 4.5 Error Handling

| Failure | Behavior |
|---------|----------|
| `gh` not installed / not authenticated | Fail pre-flight; tell user to run `gh auth login`. |
| Project Reference contains `TBD` | Pause; run discovery query; ask user to fill and re-commit. |
| Token missing `project` scope | Tell user to run `gh auth refresh -s project`. |
| Create Step 1 fails | No side effects; report and stop. |
| Create Step 2–4 fails | Report successful steps with URLs; stop; suggest manual fix or retry. |
| Read / Update single-step failure | Report; no partial-state concern. |
| Item identification: 0 matches | Report and offer to list candidates. |
| Item identification: >1 match | List candidates; ask user to pick. |

**Principle**: never swallow a GraphQL error. Always surface at least
`errors[].message` from the response to the user.

### 4.6 Pre-flight Check

Three gates before any mutation:

1. `gh auth status` succeeds.
2. No `TBD` in Project Reference.
3. Current working directory is within `niracler/random` (check via
   `git remote get-url origin` returning a URL that contains
   `niracler/random`).

## 5. Open Items (resolved before implementation)

- Exact values for all `TBD` IDs — resolved by running the discovery
  query in §4.2 once during implementation and committing the filled
  table as part of the initial skill commit.

## 6. Deferred to `random-review`

- Applying the 6 rules from `prompt.md` to audit Ready items.
- Batch promotion Backlog → Ready with AI-assisted critique.
- Deciding the final disposition of `prompt.md` (inline into
  `random-review` vs. keep as shared reference).

## 7. Implementation Plan

Tracked separately via the `writing-plans` skill (to be invoked after
this spec is approved).
