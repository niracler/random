---
name: random-manage
description: Use this skill to manage items on niracler's personal "Random"
  GitHub Project (https://github.com/users/niracler/projects/1) — including
  creating new random-dare ideas, listing items by status/priority, updating
  an item's Status (Backlog / Ready / In progress / In review / Done / Reject),
  or updating Priority (P0 / P1 / P2). Triggers on phrases like "加一条 random",
  "add to random", "random 里加 X", "random 里有什么", "show random list",
  "Ready 里有哪些", "P0 有哪些", "把 X 改成 Ready", "X 移到 Backlog",
  "close X" (→ Reject), "X 的优先级改成 P0", "把 X 的 priority 清掉",
  and "帮我 draft X 的计划" (full TODOList generation). Only activate
  inside the niracler/random repository.
---

# Random Project Manager

This skill lets Claude manage items on niracler's Random GitHub Project
by calling GitHub GraphQL via `gh api graphql`. Write operations require
a preview-and-confirm step before any mutation runs.

The Random project is how niracler tracks monthly personal challenges
(one item per month, picked randomly from the `Ready` column). Items
are GitHub issues attached to project `PVT_kwHOAXsRh84Ak2d1`.

## 1. Pre-flight Check

Before running any GraphQL call, verify all three:

1. **`gh` is authenticated.** Run `gh auth status`. If it exits non-zero
   or doesn't show the `project` scope, stop and tell the user to run
   `gh auth login` or `gh auth refresh -s project`.
2. **Working directory is inside `niracler/random`.** Run
   `git remote get-url origin` and confirm the URL contains `niracler/random`.
   If not, this skill should not activate — likely the user meant a
   different project. Stop.
3. **Project Reference (§2) has no `TBD`.** If any ID is `TBD`, this
   skill hasn't been bootstrapped. Run the discovery query at the end
   of §2 and update this file.

These checks exist because a quiet failure here cascades — e.g., an
unauthenticated `gh` produces opaque errors mid-transaction; a wrong
repo context means you'd be editing someone else's project if a
collision happened.

## 2. Project Reference

All opaque GraphQL IDs needed for mutations. These are stable across
normal use of the project. Re-run the discovery query (bottom of this
section) only if you add/rename a status column, change priority
options, or add a new label to the whitelist.

### Project & repository

- `PROJECT_ID` = `PVT_kwHOAXsRh84Ak2d1`
- `REPOSITORY_ID` = `R_kgDOHi0NjA`

### Status field

- `STATUS_FIELD_ID` = `PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o`

| Status      | Option ID   | Notes                                        |
|-------------|-------------|----------------------------------------------|
| Backlog     | `f75ad846`  | Default for new items; raw idea not yet vetted. |
| Ready       | `61e4505c`  | Vetted and in the monthly random-pick pool.  |
| In progress | `47fc9ee4`  | Currently being worked on. Also called "Doing". |
| In review   | `df73e18b`  | Work done, pending verification.             |
| Done        | `98236657`  | Completed.                                   |
| Reject      | `7dbd231a`  | Rejected; `random_dare/close_rejected.py` auto-closes these. |

**Synonym guidance:** if the user says "Doing", "做到一半",
"in progress", or "正在做", map to `In progress`. If the user says
"review", "review 中", "pending", map to `In review`. If the user says
"close" without a target status, default to `Reject`.

### Priority field

- `PRIORITY_FIELD_ID` = `PVTSSF_lAHOAXsRh84Ak2d1zgc_sBA`

| Priority | Option ID   |
|----------|-------------|
| P0       | `79628723`  |
| P1       | `0a877460`  |
| P2       | `da944a9c`  |

### Labels (whitelist — never invent new labels)

| Label        | Label ID                         |
|--------------|----------------------------------|
| practice     | `LA_kwDOHi0NjM8AAAABrgD6Ag`      |
| game         | `LA_kwDOHi0NjM8AAAABrf7AdA`      |
| dare         | `LA_kwDOHi0NjM8AAAABrgJDKg`      |
| research     | `LA_kwDOHi0NjM8AAAABrgKckg`      |
| portfolios   | `LA_kwDOHi0NjM8AAAABrgKaZA`      |
| life_habit   | `LA_kwDOHi0NjM8AAAACe5yYZQ`      |

If a user request seems to need a label outside this list, ask them
to confirm before doing anything — don't silently drop the label and
don't invent one. New labels should be a deliberate human decision,
not an LLM guess.

### Discovery query (re-run if the schema changes)

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
    labels(first: 50) { nodes { id name } }
  }
}'
```

## 3. Operations

Four operations. All write operations follow the same pattern: build a
preview, show it to the user, wait for explicit `yes`, then run the
mutation. Never mutate on ambiguous confirmation.

### 3.1 Create Item

**Triggers (default Mode A, minimal body):** "加一条 random",
"add to random", "random 里加 X", "帮我记一下：X", "加个 dare：X",
"记到 random 里".

**Triggers (Mode C, full body with TODOList):** only when the user
explicitly asks to draft or plan — "帮我 draft X 的计划",
"拆解 X 的 TODOList", "帮我规划一下 X". Mode C generates the full
Summary + TODOList + Books & Resources body; Mode A just generates
the title and a one-line summary.

**Input:** one natural-language sentence from the user.

**What Claude infers from the input:**

- `title` — bilingual, format `"EN | 中文"`. The ` | ` separator (with
  surrounding spaces) is required — `random_dare/pick.py` splits on it
  to get the English name for Telegram announcements.
- `summary` — bilingual, same `"EN | 中文"` format, one sentence.
- `labels` — pick 0-3 from the whitelist in §2 that fit the idea. If
  none fit cleanly, pick zero. **Never invent.**

**What Claude does not infer (fixed defaults):**

- `status` = Backlog. New ideas park here until a monthly review
  promotes them to Ready. This matches niracler's monthly workflow
  (rule 1 of the Random rules in the repo README).
- `priority` = unset. Skip Step 4 of the transaction entirely unless
  the user explicitly said "P0"/"P1"/"P2" in their message.
- `repository` = `niracler/random` (use `REPOSITORY_ID` from §2).

**Preview block (MANDATORY before any mutation):**

```
## 📝 即将创建：

**Title**: <title EN> | <title 中文>
**Labels**: <labels, comma-separated, or "(none)">
**Status**: Backlog
**Priority**: (unset)
**Mode**: <A or C>

**Body**:
─────
<body as it will be submitted>
─────

Confirm? (yes / edit <field> <new value> / cancel)
```

User replies:

- `yes` / `ok` / `确认` → run the 4-step transaction below.
- `edit <field> <new value>` → modify the draft, re-show the preview.
- `cancel` / `no` / anything ambiguous → abort. Do not mutate.

**4-step transaction:**

**Step 1 — create the issue:**

```bash
gh api graphql -f query='
mutation {
  createIssue(input: {
    repositoryId: "R_kgDOHi0NjA"
    title: "<title>"
    body: "<body>"
    labelIds: [<label IDs as JSON array>]
  }) {
    issue { id number url }
  }
}'
```

Capture `issue.id`, `issue.number`, `issue.url`.

**Step 2 — add the issue to the project:**

```bash
gh api graphql -f query='
mutation {
  addProjectV2ItemById(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    contentId: "<issue.id from Step 1>"
  }) {
    item { id }
  }
}'
```

Capture `item.id` — this is the `projectItemId` (format `PVTI_...`),
which is distinct from the issue ID and is what Step 3 needs.

**Step 3 — set Status to Backlog:**

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<item.id from Step 2>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o"
    value: { singleSelectOptionId: "f75ad846" }
  }) {
    projectV2Item { id }
  }
}'
```

**Step 4 — set Priority** (only if the user explicitly specified one;
otherwise skip this step entirely):

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<item.id from Step 2>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_sBA"
    value: { singleSelectOptionId: "<P0/P1/P2 option ID from §2>" }
  }) {
    projectV2Item { id }
  }
}'
```

After all steps succeed, report to the user with the issue URL, the
final status, and (if set) priority.

**Error handling — see §5.** Key principle: if any step fails, report
what succeeded (with URL) and stop. Do not auto-delete the created
issue to "roll back" — that has worse failure modes than honest
partial-state reporting.

### 3.2 List Items

**Triggers:** "show random list", "random 里有什么", "list random items",
"Ready 里有哪些", "show Backlog", "P0 有哪些", "所有 practice 的",
"random 清单".

**Behavior:** fetch all items in one GraphQL call (`first: 100` is
plenty for this project), then filter client-side. Client-side
filtering is simpler and supports compound queries like "P0 里还在
Ready 的 practice tag 的" without writing a new GraphQL query each time.

**Query:**

```bash
gh api graphql -f query='
query {
  node(id: "PVT_kwHOAXsRh84Ak2d1") {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id
          fieldValues(first: 8) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
          content {
            ... on Issue {
              number
              title
              url
              state
              labels(first: 10) { nodes { name } }
            }
          }
        }
      }
    }
  }
}'
```

**Output:** markdown table with columns `# | Title | Status | Priority | Labels`.

**Row-count policy:** if more than 15 items match the user's filter,
show only the filtered subset. If the user explicitly asks for "全部"
/ "show all" / "full list", dump everything.

**No confirmation** — read-only.

### 3.3 Update Status

**Triggers:** "把 X 改成 Ready", "X 移到 Backlog", "X 标成 In progress",
"X 做到一半了" (→ In progress), "X 完成了" (→ Done), "close X" (→ Reject),
"reject X", "X 进入 review" (→ In review).

**Item identification (shared with §3.4):**

1. Run the List query (§3.2) to get all items with their
   `projectItemId`, `content.number`, and `content.title`.
2. Match the user's reference "X":
   - If "X" is a number (`#42` or `42`) — match `content.number` exactly.
   - Otherwise — case-insensitive substring match on `content.title`.
     Remember titles are `"EN | 中文"` format, so the user might say
     either side of the pipe.
3. Resolve matches:
   - **0 matches:** reply "no item matched 'X'. Want me to show the
     current list so you can pick one?"
   - **1 match:** proceed to confirmation.
   - **>1 matches:** list candidates as `#num title (Status)` and ask
     the user to pick by number.

**Confirmation format:**

```
即将把 [#<number> <title>]
Status: <current> → <target>

Confirm? (yes / cancel)
```

**Mutation (after `yes`):**

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<projectItemId>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o"
    value: { singleSelectOptionId: "<target option ID from §2>" }
  }) {
    projectV2Item { id }
  }
}'
```

### 3.4 Update Priority

**Triggers (set):** "把 X 调成 P0", "X 降到 P2", "X 升 P0",
"X 的优先级改成 P1", "X 标成 P0".

**Triggers (clear):** "把 X 的 priority 清掉", "取消 X 的优先级",
"X 的 priority 不要了", "clear X's priority".

**Item identification:** same algorithm as §3.3.

**Set-priority mutation:**

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<projectItemId>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_sBA"
    value: { singleSelectOptionId: "<P0/P1/P2 option ID from §2>" }
  }) {
    projectV2Item { id }
  }
}'
```

**Clear-priority mutation** — uses a **different** mutation name,
easy to miss:

```bash
gh api graphql -f query='
mutation {
  clearProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<projectItemId>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_sBA"
  }) {
    projectV2Item { id }
  }
}'
```

**Confirmation formats:**

- Set: `即将把 [#<n> <title>]  Priority: <current> → <target>  Confirm?`
- Clear: `即将清除 [#<n> <title>] 的 Priority (current: <current>).  Confirm?`

## 4. Create Body Template

### Mode A (minimal body)

```markdown
# title
{Title EN} | {Title 中文}

## Summary
{Summary EN} | {Summary 中文}
```

Two sections only. No TODOList. The Summary line is **one sentence**
bilingual. Keep it tight; the user can flesh out the body later with
Mode C or manually.

### Mode C (draft plan body)

When the user explicitly asks to draft / plan, use this template
verbatim (replace `{...}` placeholders, keep section headers intact):

```markdown
# title
{Title EN} | {Title 中文}

## Summary
{Summary EN} | {Summary 中文}

## TODOList

### Step 1: {Phase 1 name} (1-2 weeks)

- [ ] **{Task topic}**:
  - {Sub-step or focus area}
  - {Sub-step or focus area}

- [ ] **{Task topic}**:
  - {Sub-step or focus area}

### Step 2: {Phase 2 name} (1-2 weeks)

- [ ] ...

### Step 3: {Phase 3 name} (1-2 weeks)

- [ ] ...

### Books & Resources

- [ ] [{Resource name}]({URL})
- [ ] [{Resource name}]({URL})
```

Step count is typically 3. If the topic naturally splits into more or
fewer phases, adjust — the headers `## Summary`, `## TODOList`, and
`### Books & Resources` must stay; `### Step N:` is a flexible scaffold.

### Bilingual rules (both modes)

- **Title** must use `"EN | 中文"` with space-pipe-space.
  `random_dare/pick.py` builds the Telegram message by concatenating
  the title with extra context, then splits on the first `|` to recover
  the English title. The separator must therefore live inside the
  GitHub issue title — without it, the English-name extraction breaks.
- **Summary** line should also be `"EN | 中文"`.
- TODOList items and Books & Resources entries can be single-language
  (English is fine). Don't force bilingual everywhere — it makes the
  body noisy.

## 5. Error Handling

**Core principle:** never swallow a GraphQL error. Always surface at
least `errors[].message` from the response. Users can recover from
clear error messages; they cannot recover from a silent failure.

| Failure | What to do |
|---------|------------|
| `gh` not authenticated | §1 pre-flight fails. Tell user: `gh auth login`. |
| Project Reference has `TBD` | §1 pre-flight fails. Tell user to run the §2 discovery query and update this file. |
| Token missing `project` scope | Tell user: `gh auth refresh -s project`. |
| Wrong working directory | §1 pre-flight fails. Tell user this skill is for `niracler/random` only. |
| Create Step 1 fails | No side effects. Surface `errors[].message` and stop. |
| Create Step 2 fails | Issue exists but not on the project board. Report `issue.url` so the user has the link. Offer: "want me to retry Step 2, or add it to the board manually?" |
| Create Step 3 fails | Item is on the board with no Status (appears in the "No Status" column). Report and offer retry. |
| Create Step 4 fails | Priority unset; non-critical. Report and offer retry. |
| Update mutation fails | Single-step operation — no partial state. Report the error. |
| List query fails | Report and stop. |
| Item identification: 0 matches | Report. Offer to show the current list. |
| Item identification: >1 matches | List candidates. Ask the user to pick. |

**Things this skill must never do:**

- Delete an issue automatically to "clean up" a failed Create. The user
  may have valuable context in the partial state; rollback causes
  worse data loss than honest reporting.
- Silently retry a failed mutation. Retries hide intermittent failures
  that the user should know about.
- Use any Project / Field / Option ID not listed in §2.
- Create a new label. If a label seems useful, ask the user to add it
  manually on GitHub first, then re-run.
