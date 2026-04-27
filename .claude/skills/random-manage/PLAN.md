# random-manage Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill at `.claude/skills/random-manage/SKILL.md` that lets Claude manage items on niracler's Random GitHub Project via natural-language commands (Create / List / Update Status / Update Priority).

**Architecture:** Single-file skill. All GraphQL IDs (project, fields, options, labels) hardcoded after a one-time discovery step. Write operations use `gh api graphql` invoked by Claude per skill instructions. Write operations require preview-and-confirm before mutation.

**Tech Stack:** Markdown (SKILL.md), GitHub GraphQL API (v2 Projects), `gh` CLI. No Python, no tests folder — verification is dry-run queries + end-to-end manual test.

**Spec reference:** `./DESIGN.md` (sibling file).

---

## Files

- **Create:** `.claude/skills/random-manage/SKILL.md` — the skill itself.
- **Already exists:** `.claude/skills/random-manage/DESIGN.md` — approved spec.
- **Already exists:** `.claude/skills/random-manage/PLAN.md` — this file.
- **No tests folder** — skill correctness verified by dry-run GraphQL calls and one end-to-end manual integration test.

---

## Commit Policy

Per niracler's global CLAUDE.md: **"NEVER commit changes unless the user explicitly asks to."** Each task lists a suggested commit command, but the executing agent/developer must **ask the user before running `git commit`**. Batching all commits until the end is also acceptable if the user prefers.

---

## Task 1: Discovery — collect all GraphQL IDs

**Files:**
- Temporary: `/tmp/random-manage-discovery.json`

**Purpose:** Resolve every `TBD` in DESIGN.md §4.2 by querying the live project schema once.

- [ ] **Step 1.1: Verify `gh` is authenticated with `project` scope**

Run:
```bash
gh auth status
```
Expected: output includes `Logged in to github.com` and the token scopes include `project`. If `project` missing, run `gh auth refresh -s project` first.

- [ ] **Step 1.2: Run the discovery query**

Run:
```bash
gh api graphql -f query='
query {
  node(id: "PVT_kwHOAXsRh84Ak2d1") {
    ... on ProjectV2 {
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id
            name
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
}' > /tmp/random-manage-discovery.json
```
Expected: exit code 0, JSON file written.

- [ ] **Step 1.3: Extract the IDs into a reference block**

Run:
```bash
cat /tmp/random-manage-discovery.json | jq '.'
```

From the output, record the following in a scratch note (paste into next task):

- `REPOSITORY_ID` = `data.repository.id`
- Find field named "Status" → `STATUS_FIELD_ID` + each option's `id` by `name` (Backlog / Ready / Doing / Done / Reject)
- Find field named "Priority" → `PRIORITY_FIELD_ID` + option IDs for P0 / P1 / P2
- Label IDs for: `practice`, `game`, `dare`, `research`, `portfolios`, `life_habit` (from `data.repository.labels.nodes[].{id, name}`)

**If any expected label is missing** from the label list, **stop and ask the user**: either the label doesn't exist yet (user decides whether to create it) or the name is different (user corrects the whitelist). Do not invent labels.

**If the Status field's 5 expected values don't all exist** (e.g., no "Backlog" but there's a "Todo"), stop and ask the user to reconcile DESIGN.md before continuing.

- [ ] **Step 1.4: Commit point — nothing to commit yet**

No files changed. Proceed to Task 2.

---

## Task 2: SKILL.md skeleton + frontmatter + Project Reference

**Files:**
- Create: `.claude/skills/random-manage/SKILL.md`

**Purpose:** Lay down the full structure with all six sections as headers, frontmatter fully filled, Project Reference table populated from Task 1's discovery output. Operation bodies are empty placeholders to be filled in later tasks.

- [ ] **Step 2.1: Write the skeleton file**

Create `/Users/niracler/code/nini-dev/repos/random/.claude/skills/random-manage/SKILL.md` with this content (substituting `<discovered>` values from Task 1.3 scratch note):

````markdown
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

# Random Project Manager

Manages items on the Random GitHub Project via `gh api graphql`.

## 1. Pre-flight Check

Before running any mutation, verify:

1. `gh auth status` is authenticated (fail fast with error if not)
2. The Project Reference section below has no `TBD` values (if any, this
   skill is not yet bootstrapped — do not proceed)
3. Current working directory is within the `niracler/random` repo:
   ```bash
   git remote get-url origin
   ```
   The URL must contain `niracler/random`. If not, the skill must not activate.

## 2. Project Reference

**Constants used by all GraphQL calls below.** Never invoke any mutation
if any value is `TBD` — the skill is not yet bootstrapped.

### Project & Repository
- `PROJECT_ID` = `PVT_kwHOAXsRh84Ak2d1`
- `REPOSITORY_ID` = `<discovered>`

### Status Field
- `STATUS_FIELD_ID` = `PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o`

| Status  | Option ID       |
|---------|-----------------|
| Backlog | `<discovered>`  |
| Ready   | `<discovered>`  |
| Doing   | `47fc9ee4`      |
| Done    | `<discovered>`  |
| Reject  | `<discovered>`  |

### Priority Field
- `PRIORITY_FIELD_ID` = `<discovered>`

| Priority | Option ID      |
|----------|----------------|
| P0       | `<discovered>` |
| P1       | `<discovered>` |
| P2       | `<discovered>` |

### Labels (whitelist — do not invent new labels)

| Label        | Label ID       |
|--------------|----------------|
| practice     | `<discovered>` |
| game         | `<discovered>` |
| dare         | `<discovered>` |
| research     | `<discovered>` |
| portfolios   | `<discovered>` |
| life_habit   | `<discovered>` |

### Discovery query (re-run if the project schema changes)

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

### 3.1 Create Item

(to be filled in Task 4)

### 3.2 List Items

(to be filled in Task 5)

### 3.3 Update Status

(to be filled in Task 6)

### 3.4 Update Priority

(to be filled in Task 7)

## 4. Create Body Template

(to be filled in Task 8)

## 5. Error Handling

(to be filled in Task 9)
````

- [ ] **Step 2.2: Verify no `<discovered>` markers remain in the Project Reference section**

Run:
```bash
grep -c '<discovered>' /Users/niracler/code/nini-dev/repos/random/.claude/skills/random-manage/SKILL.md
```
Expected: `0`. If > 0, go back to Task 1 and fix the scratch note.

Note: `TBD` may legitimately appear later in draft placeholders; only `<discovered>` means "forgot to substitute an ID".

- [ ] **Step 2.3: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): scaffold skill with Project Reference"
```

---

## Task 3: Implement §3.2 List Items (simplest operation, no mutations)

**Files:**
- Modify: `.claude/skills/random-manage/SKILL.md` — replace the §3.2 placeholder.

**Purpose:** Start with read-only since it's safest and the query is reused by Task 5 and Task 6 for item identification.

- [ ] **Step 3.1: Replace §3.2 with the full List operation spec**

Find `### 3.2 List Items\n\n(to be filled in Task 5)` and replace with:

````markdown
### 3.2 List Items

**Triggers:** "show random list", "random 里有什么", "list random items",
"Ready 里有哪些", "show Backlog", "P0 有哪些", "所有 practice tag 的".

**Behavior:** Fetch all items in one GraphQL call (up to 100), then filter
client-side based on the user's request.

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
            ... on Issue { number title url labels(first: 10) { nodes { name } } }
          }
        }
      }
    }
  }
}'
```

**Output:** Markdown table with columns `# | Title | Status | Priority | Labels`.

- **Filter:** apply in Claude's response synthesis based on the user's wording.
  Examples: `"P0 有哪些"` → filter Priority == "P0"; `"Ready 里的 practice"` → filter Status == "Ready" AND `practice` in labels.
- **Row count policy:** if more than 15 items match, show only the filtered subset. If the user explicitly says "全部 / show all / full list", dump everything.

**No confirmation required.** Read-only operation.
````

- [ ] **Step 3.2: Dry-run the query**

Run:
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
            ... on Issue { number title url labels(first: 10) { nodes { name } } }
          }
        }
      }
    }
  }
}' | jq '.data.node.items.nodes | length'
```
Expected: a number > 0 (your actual item count). If `null` or error, the query is wrong; fix before continuing.

- [ ] **Step 3.3: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): implement List Items operation"
```

---

## Task 4: Create a test item via GitHub UI (manual bootstrap for Tasks 5–7)

**Purpose:** Tasks 5, 6, 7 need a real item to mutate. Since Create (Task 8) is the most complex and last, we manually create one test item to use as a stable target.

- [ ] **Step 4.1: Create test item on GitHub**

Open https://github.com/niracler/random/issues/new in browser. Fill in:

- **Title:** `Test random-manage Skill | random-manage skill 测试`
- **Body:**
  ```markdown
  # title
  Test random-manage Skill | random-manage skill 测试

  ## Summary
  Temporary issue for skill verification. Will be closed after testing. |
  临时测试用，验证完即关闭。
  ```
- **Labels:** `practice`

Submit. Note the issue number (e.g., `#50`).

- [ ] **Step 4.2: Add the test issue to the Random project**

On the issue page, in the right sidebar, click "Projects" → add to the Random project. Set Status = `Backlog` (no Priority).

- [ ] **Step 4.3: Record the projectItemId**

Run:
```bash
gh api graphql -f query='
query {
  node(id: "PVT_kwHOAXsRh84Ak2d1") {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id
          content { ... on Issue { number title } }
        }
      }
    }
  }
}' | jq '.data.node.items.nodes[] | select(.content.title | contains("Test random-manage"))'
```
Expected: an object with `"id": "PVTI_..."`. Record this `TEST_PROJECT_ITEM_ID` and `TEST_ISSUE_NUMBER` in a scratch note for Tasks 5–7.

---

## Task 5: Implement §3.3 Update Status

**Files:**
- Modify: `.claude/skills/random-manage/SKILL.md` — replace §3.3 placeholder.

- [ ] **Step 5.1: Replace §3.3 with the full Update Status spec**

Find `### 3.3 Update Status\n\n(to be filled in Task 6)` and replace with:

````markdown
### 3.3 Update Status

**Triggers:** "把 X 改成 Ready", "X 移到 Backlog", "把 X 标成 Doing",
"close X" (→ Reject), "reject X".

**Item identification (shared with §3.4):**

1. Run the List query (§3.2) to get all items with their `projectItemId` and `content.{number, title}`.
2. Match the user's reference "X":
   - If "X" is a number (`#42` or `42`) → match `content.number`.
   - Otherwise → case-insensitive substring match on `content.title`.
3. Resolve matches:
   - **0 matches:** Reply with "no item matched 'X'. Should I list Ready items?"
   - **1 match:** proceed to confirmation.
   - **>1 matches:** list all candidates (`#num title`) and ask the user to pick.

**Confirmation format:**

```
即将把 [#<number> <title>]
Status: <current> → <target>

Confirm? (yes / cancel)
```

**Mutation** (after `yes`):

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

**Error handling:** surface the full GraphQL response (at least
`errors[].message`) to the user. No partial-state concerns — single mutation.
````

- [ ] **Step 5.2: Dry-run the mutation against the test item**

Using `TEST_PROJECT_ITEM_ID` from Task 4.3 and the Ready option ID from Task 1.3, run:

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<TEST_PROJECT_ITEM_ID>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o"
    value: { singleSelectOptionId: "<Ready option ID>" }
  }) {
    projectV2Item { id }
  }
}'
```
Expected: JSON with `data.updateProjectV2ItemFieldValue.projectV2Item.id` matching `TEST_PROJECT_ITEM_ID`, no `errors` key.

- [ ] **Step 5.3: Verify in browser**

Open https://github.com/users/niracler/projects/1/views/1 and confirm the test item shows Status = Ready.

- [ ] **Step 5.4: Revert test item to Backlog for Task 6**

Re-run Step 5.2 with the Backlog option ID instead of Ready.

- [ ] **Step 5.5: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): implement Update Status operation"
```

---

## Task 6: Implement §3.4 Update Priority (including clear variant)

**Files:**
- Modify: `.claude/skills/random-manage/SKILL.md` — replace §3.4 placeholder.

- [ ] **Step 6.1: Replace §3.4 with the full Update Priority spec**

Find `### 3.4 Update Priority\n\n(to be filled in Task 7)` and replace with:

````markdown
### 3.4 Update Priority

**Triggers:** "把 X 调成 P0", "X 降到 P2", "X 升 P0", "X 的优先级改成 P1",
"把 X 的 priority 清掉", "取消 X 的优先级".

**Item identification:** same algorithm as §3.3 (shared).

**Set priority mutation:**

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<projectItemId>"
    fieldId: "<PRIORITY_FIELD_ID from §2>"
    value: { singleSelectOptionId: "<P0/P1/P2 option ID from §2>" }
  }) {
    projectV2Item { id }
  }
}'
```

**Clear priority mutation** (when user says "清掉 / 取消 / clear / unset"):

```bash
gh api graphql -f query='
mutation {
  clearProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<projectItemId>"
    fieldId: "<PRIORITY_FIELD_ID from §2>"
  }) {
    projectV2Item { id }
  }
}'
```

**Confirmation format:**
- Set: `即将把 [#<n> <title>]  Priority: <current> → <target>  Confirm?`
- Clear: `即将清除 [#<n> <title>] 的 Priority (current: <current>). Confirm?`
````

- [ ] **Step 6.2: Dry-run set-priority against test item**

Run the set mutation with `TEST_PROJECT_ITEM_ID`, `PRIORITY_FIELD_ID`, and P1 option ID:

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<TEST_PROJECT_ITEM_ID>"
    fieldId: "<PRIORITY_FIELD_ID>"
    value: { singleSelectOptionId: "<P1 option ID>" }
  }) {
    projectV2Item { id }
  }
}'
```
Expected: success, no `errors`. Verify in browser that test item now shows P1.

- [ ] **Step 6.3: Dry-run clear-priority against test item**

```bash
gh api graphql -f query='
mutation {
  clearProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<TEST_PROJECT_ITEM_ID>"
    fieldId: "<PRIORITY_FIELD_ID>"
  }) {
    projectV2Item { id }
  }
}'
```
Expected: success. Verify in browser that test item's Priority is now empty.

- [ ] **Step 6.4: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): implement Update Priority operation"
```

---

## Task 7: Implement §3.1 Create Item (largest operation)

**Files:**
- Modify: `.claude/skills/random-manage/SKILL.md` — replace §3.1 placeholder.

- [ ] **Step 7.1: Replace §3.1 with the full Create Item spec**

Find `### 3.1 Create Item\n\n(to be filled in Task 4)` and replace with:

````markdown
### 3.1 Create Item

**Triggers (Mode A — default, minimal body):**
"加一条 random", "add to random", "random 里加 X", "帮我记一下：X",
"加个 dare：X".

**Triggers (Mode C — full body with TODOList):**
User explicitly asks to draft a plan: "帮我 draft 计划", "拆解 X 的 TODOList",
"帮我规划一下 X".

**Input contract:**
- Minimum required: one natural-language sentence from the user describing the idea.
- Claude infers:
  - `title` — bilingual, formatted `"EN | 中文"` (the ` | ` separator is required; `rand.py` depends on it).
  - `summary` — bilingual, formatted `"EN | 中文"`.
  - `labels` — **only** from the whitelist in §2 (`practice`, `game`, `dare`, `research`, `portfolios`, `life_habit`). Pick 0–3 that fit. **Never invent new labels.**
- Claude does NOT infer these — they are fixed:
  - `repository` = `niracler/random` (use `REPOSITORY_ID` from §2)
  - `status` = Backlog (use Backlog option ID from §2)
  - `priority` = unset (skip Step 4 of the transaction entirely)
- Body — see §4 Create Body Template.

**Preview format (mandatory before any mutation):**

```
## 📝 即将创建：

**Title**: <title>
**Labels**: <labels>
**Status**: Backlog
**Priority**: (unset)
**Mode**: <A | C>

**Body**:
─────
<body as it will be submitted>
─────

Confirm? (yes / edit <field> <new value> / cancel)
```

User responses:
- `yes` / `ok` / `确认` → execute the 4-step transaction.
- `edit <field> <new>` → update the draft and re-show the preview.
- `cancel` / `no` → abort. No mutation runs.

**4-step transaction (executed only after `yes`):**

**Step 1** — Create the issue:

```bash
gh api graphql -f query='
mutation {
  createIssue(input: {
    repositoryId: "<REPOSITORY_ID>"
    title: "<title>"
    body: "<body>"
    labelIds: ["<label ID 1>", "<label ID 2>"]
  }) {
    issue { id number url }
  }
}'
```
Capture `issue.id` (for Step 2), `issue.number`, `issue.url` (for user report).

**Step 2** — Add the issue to the project:

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
Capture `item.id` (the `projectItemId`, for Step 3).

**Step 3** — Set Status to Backlog:

```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<item.id from Step 2>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o"
    value: { singleSelectOptionId: "<Backlog option ID>" }
  }) {
    projectV2Item { id }
  }
}'
```

**Step 4** — Skipped. (Priority is unset by default; this step only runs if the user explicitly specified a priority in their request, which Mode A does not support — they'd need to set it after with §3.4.)

**Error handling (per §5 for details):**
- Step 1 fails → nothing created, report and stop.
- Step 2 fails → issue exists but not on board. Report `issue.url` and offer to retry Step 2 or let user add manually.
- Step 3 fails → item on board but no Status (shows under "No Status" column). Report and offer to retry or fix manually.
- **No automatic rollback.** Never delete the created issue.
````

- [ ] **Step 7.2: Dry-run each of the 4 steps individually against a fresh test item**

**CAUTION:** this step actually creates a new GitHub issue. We'll close it in Task 9.

Step 1 — create issue:
```bash
gh api graphql -f query='
mutation {
  createIssue(input: {
    repositoryId: "<REPOSITORY_ID>"
    title: "Dry-run Create test | Create 干跑测试"
    body: "Temporary issue from plan Task 7. Will be closed."
    labelIds: ["<practice label ID>"]
  }) {
    issue { id number url }
  }
}'
```
Expected: `data.createIssue.issue.{id, number, url}` present.

Step 2 — add to project:
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
Expected: `data.addProjectV2ItemById.item.id` present.

Step 3 — set Backlog:
```bash
gh api graphql -f query='
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwHOAXsRh84Ak2d1"
    itemId: "<item.id from Step 2>"
    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o"
    value: { singleSelectOptionId: "<Backlog option ID>" }
  }) {
    projectV2Item { id }
  }
}'
```
Expected: success.

Open https://github.com/users/niracler/projects/1/views/1 and verify the dry-run item appears in Backlog with the `practice` label.

- [ ] **Step 7.3: Close the dry-run issue as not planned**

```bash
gh api graphql -f query='
mutation {
  closeIssue(input: {
    issueId: "<issue.id from Step 1>"
    stateReason: NOT_PLANNED
  }) {
    issue { state }
  }
}'
```
Expected: `data.closeIssue.issue.state = "CLOSED"`. The original test item from Task 4 is untouched.

- [ ] **Step 7.4: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): implement Create Item operation"
```

---

## Task 8: Implement §4 Create Body Template

**Files:**
- Modify: `.claude/skills/random-manage/SKILL.md` — fill in §4.

- [ ] **Step 8.1: Append/replace §4 with the body template spec**

Find `## 4. Create Body Template\n\n(to be filled in Task 8)` (or add §4 if the skeleton placed it elsewhere) and ensure its content is:

````markdown
## 4. Create Body Template

### Mode A (minimal body)

```markdown
# title
{Title EN} | {Title CN}

## Summary
{Summary EN} | {Summary CN}
```

Two sections only. No TODOList.

### Mode C (draft plan body)

When operating in Mode C, read `../../../prompt.md` and use the structure
shown in its bottom-half example as the exact template for the generated
body. Fill in content based on the user's request. Keep these headers
unchanged: `## Summary`, `## TODOList`, `### Step 1:` / `### Step 2:` /
`### Step 3:`, `### Books & Resources`.

### Bilingual rules (both modes)

- **Title** must use `"EN | 中文"` with space-pipe-space separator.
  `rand.py` depends on this separator.
- **Summary** line must also use `"EN | 中文"`.
- TODOList items and Books & Resources may be single-language (English is fine).
````

- [ ] **Step 8.2: Verify prompt.md path resolves**

Run:
```bash
ls /Users/niracler/code/nini-dev/repos/random/prompt.md
```
Expected: file exists. If missing, the relative-path reference in SKILL.md is broken — stop and talk to the user.

- [ ] **Step 8.3: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): add Create Body Template section"
```

---

## Task 9: Implement §5 Error Handling

**Files:**
- Modify: `.claude/skills/random-manage/SKILL.md` — fill in §5.

- [ ] **Step 9.1: Replace §5 placeholder**

Find `## 5. Error Handling\n\n(to be filled in Task 9)` and replace with:

````markdown
## 5. Error Handling

**Principle:** never swallow a GraphQL error. Always surface at least
`errors[].message` from the response.

| Failure | Behavior |
|---------|----------|
| `gh` not authenticated | Pre-flight (§1) fails. Tell user to run `gh auth login`. |
| Project Reference contains `TBD` | Halt. Ask user to run the discovery query in §2 and fill the table. |
| Token missing `project` scope | Tell user to run `gh auth refresh -s project`. |
| Create Step 1 fails | No side effects. Report the `errors[].message` and stop. |
| Create Step 2 fails | Issue exists but not on project board. Report `issue.url`. Offer to retry Step 2 or let user add manually. |
| Create Step 3 fails | Item on board with no Status (lives in "No Status" column). Report and offer retry. |
| Create Step 4 fails | (only runs if priority specified) Priority unset; non-critical. Report and offer retry. |
| Update Status / Priority mutation fails | Single-step operation. Report `errors[].message`. No partial state. |
| List query fails | Report and stop. |
| Item identification: 0 matches | Reply "no item matched 'X'." Offer to show the current list. |
| Item identification: >1 matches | List all candidates with `#num title`. Ask user to pick. |

**Never:**
- Automatically delete an issue to "roll back" a failed Create.
- Silently retry failed mutations without telling the user.
- Invent Project / Field / Option IDs not present in §2.
- Invent label names not present in §2's whitelist.
````

- [ ] **Step 9.2: Close the test item from Task 4**

The main test item is no longer needed. Close it:
```bash
gh issue close <TEST_ISSUE_NUMBER> --repo niracler/random --reason "not planned"
```
Expected: issue marked closed.

- [ ] **Step 9.3: Suggested commit (ask user first)**

```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "feat(random-manage): add Error Handling section"
```

---

## Task 10: End-to-end integration test

**Purpose:** Full verification that Claude can load and use the skill in a natural conversation.

- [ ] **Step 10.1: Start a fresh Claude Code session in `repos/random`**

```bash
cd /Users/niracler/code/nini-dev/repos/random
claude
```
(Or open Claude Code in the IDE with `repos/random` as working directory.)

- [ ] **Step 10.2: Test Create (Mode A)**

Ask Claude: `加一条 random：学 Tauri，顺便练 Rust`

Expected behavior:
- Claude announces it's using the `random-manage` skill.
- Pre-flight check runs (reports OK).
- Preview block appears with a bilingual title, bilingual summary, `practice` label inferred, Status=Backlog, Priority=unset.
- Claude waits for confirmation.

Reply: `yes`

Expected:
- 3-step transaction runs (Step 4 skipped since priority unset).
- Final message: "Created #<n>, added to project, Status=Backlog" with URL.

Open the project board and verify a new Backlog item appeared.

- [ ] **Step 10.3: Test List**

Ask: `random 里 Backlog 有什么`

Expected: Claude fetches list, filters to Backlog rows, shows markdown table. The item from Step 10.2 should appear.

- [ ] **Step 10.4: Test Update Status**

Ask: `把 Learning Tauri 改成 Ready` (or whatever title was generated).

Expected:
- Claude finds the item by substring match.
- Confirmation preview: `Status: Backlog → Ready`.

Reply: `yes`. Verify on board.

- [ ] **Step 10.5: Test Update Priority (set + clear)**

Ask: `Learning Tauri 调成 P1`. Confirm. Verify P1 on board.

Ask: `把 Learning Tauri 的 priority 清掉`. Confirm. Verify Priority is empty.

- [ ] **Step 10.6: Test Item identification edge cases**

Ask: `把 xyz-never-exists 改成 Done` → Expected: "no item matched 'xyz-never-exists'".

If there are multiple items whose title contains a common word (e.g., "Learning"), ask: `把 Learning 改成 Done` → Expected: Claude lists candidates and asks which.

- [ ] **Step 10.7: Close the integration test issue**

```bash
gh issue close <integration test issue number> --repo niracler/random --reason "not planned"
```

- [ ] **Step 10.8: Suggested commit (ask user first)**

If Task 10 surfaced any bugs in SKILL.md, fix them and commit:
```bash
git add .claude/skills/random-manage/SKILL.md
git commit -m "fix(random-manage): <specific fix>"
```

If no bugs, no commit needed here.

---

## Task 11: Final cleanup and commit DESIGN.md + PLAN.md

**Files:**
- Already present: `DESIGN.md`, `PLAN.md`, `SKILL.md`.

- [ ] **Step 11.1: Verify directory contents**

Run:
```bash
ls -la /Users/niracler/code/nini-dev/repos/random/.claude/skills/random-manage/
```
Expected: three files — `DESIGN.md`, `PLAN.md`, `SKILL.md`.

- [ ] **Step 11.2: Verify no `TBD` or `<discovered>` markers remain in SKILL.md**

Run:
```bash
grep -E 'TBD|<discovered>|\(to be filled' /Users/niracler/code/nini-dev/repos/random/.claude/skills/random-manage/SKILL.md
```
Expected: no matches. If any matches, the relevant task wasn't completed.

- [ ] **Step 11.3: Suggested commit (ask user first)**

If DESIGN.md and PLAN.md weren't committed earlier:
```bash
git add .claude/skills/random-manage/DESIGN.md .claude/skills/random-manage/PLAN.md
git commit -m "docs(random-manage): add design and implementation plan"
```

---

## Self-Review (completed during plan authoring)

- **Spec coverage:** each DESIGN.md section maps to tasks — §4.1 frontmatter / §4.2 Project Reference → Task 2; §4.3.1 Create → Task 7; §4.3.2 List → Task 3; §4.3.3 Update Status → Task 5; §4.3.4 Update Priority → Task 6; §4.4 Body Template → Task 8; §4.5 Error Handling → Task 9; §4.6 Pre-flight Check → included in Task 2 skeleton (Section §1 of SKILL.md). All 13 Decision Log entries are reflected in task content.
- **Placeholder scan:** each task shows exact code to paste, exact commands to run with expected output. Discovery values are `<discovered>` placeholders that the executing agent fills from Task 1 output (not plan failures — they're intentional substitution points).
- **Type consistency:** `TEST_PROJECT_ITEM_ID`, `TEST_ISSUE_NUMBER`, `REPOSITORY_ID`, `PRIORITY_FIELD_ID`, and `STATUS_FIELD_ID` are used consistently across Tasks 1, 4, 5, 6, 7. Option IDs (Backlog / Ready / Doing / Done / Reject / P0 / P1 / P2) and label IDs are referenced the same way throughout.

---

## Deferred (explicitly not in this plan)

- `random-review` skill (the second skill) — separate spec + plan cycle later.
- Body / TODOList editing of existing items.
- Label editing on existing items.
- Final disposition of `prompt.md` (inline into `random-review` vs. keep as shared reference).
