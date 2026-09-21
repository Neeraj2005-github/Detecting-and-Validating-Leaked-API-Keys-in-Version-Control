# SecretGuard — Frontend Build Instructions (O4 scope, FINAL)

## React dashboard — no authentication

Paste into the repo as `FRONTEND_INSTRUCTIONS.md`. This is O4 scope — build once M5/M8
(verification + risk scoring) exist on the backend, or against mocked API responses now.
Auth is explicitly out of scope (single-user, local/demo deployment assumed) — document
this as a deliberate scope decision in the paper, not an oversight.

---

## 0. Design direction (read before writing any component)

Reference aesthetic: GitGuardian / Snyk / Datadog-style security dashboards — dark-mode
first, data-dense, color-coded by severity, not a generic admin-panel template.

**Non-negotiables:**

- Dark theme default (light-mode toggle optional, not required)
- Severity palette must be colorblind-safe — pair color with an icon or label, never
  color alone (e.g., "Critical" badge is dark red + a filled circle icon + the word "Critical")
- Every data view has an explicit empty state and a loading skeleton — never a blank screen
- Every finding shows a visible state-transition timeline:
  `LEAKED_VALID → ROTATED → CONFIRMED_REMEDIATED` with timestamps, not just a current-status badge

---

## 1. Stack & versions

```
react==18.*
typescript==5.*
tailwindcss==3.*
shadcn/ui (latest, via CLI)
recharts==2.*
react-router-dom==6.*
axios==1.*
```

---

## 2. Pages to build

### 2.1 Dashboard overview (`/` — this is now the landing page, no login redirect)

- Top row: 4 summary cards — Total Findings, Critical (unrotated), Avg. MTTR, Findings Verified Today
- Main panel: risk-ranked worklist table (sortable by Risk Score descending by default)

- Columns: Secret Type, Repository, Risk Score (badge), State (badge + relative time), Last Checked
- Row click → navigates to finding detail
- Side panel: MTTR trend line chart (Recharts `LineChart`) over the last 30 days

### 2.2 Finding detail (`/findings/:id`)

- Header: secret type, repo, file path, commit SHA (short form, linked to GitHub if public)
- **Risk score breakdown** — this is your explainability differentiator, make it visible:
a horizontal stacked bar or 4-row list showing each component (Validity 40%, Blast Radius 25%,
Exposure Context 20%, Secret-Class Criticality 15%) with its contribution to the 0–100 total
- State timeline component (see 0. above) — vertical stepper, one entry per state transition
- Never render the actual secret value — show only `secret_type` + masked hash (`****a91f`)

### 2.3 Repositories (`/repositories`)

- List of scanned repos with last-scan timestamp, finding count, "Scan now" button
- "Add repository" form (URL input) → calls `POST /repositories`

### 2.4 Settings (`/settings`)

- Sandbox/provider credential status (connected/not connected) per provider — read-only
status indicators, never let the frontend display or edit a live credential value
- Re-check interval configuration (6–12h, matches APScheduler config) — dropdown, not free text

---

## 3. Component library (shadcn/ui-based)

```
src/
├── components/
│   ├── ui/                      # shadcn/ui generated components — do not hand-edit
│   ├── SeverityBadge.tsx         # props: level: 'critical'|'high'|'medium'|'low'
│   ├── RiskScoreBreakdown.tsx    # props: breakdown: {validity, blastRadius, exposure, criticality}
│   ├── StateTimeline.tsx         # props: transitions: {state, timestamp}[]
│   ├── SummaryCard.tsx           # props: label, value, trend?: number
│   ├── FindingsTable.tsx         # sortable, paginated
│   ├── MTTRTrendChart.tsx        # Recharts wrapper
│   ├── EmptyState.tsx            # props: icon, title, description, action?
│   └── LoadingSkeleton.tsx
├── pages/
│   ├── DashboardPage.tsx
│   ├── FindingDetailPage.tsx
│   ├── RepositoriesPage.tsx
│   └── SettingsPage.tsx
├── api/
│   ├── client.ts                 # plain axios instance, no auth headers
│   ├── findings.ts
│   └── repositories.ts
└── types/
    └── index.ts                  # Finding, RiskBreakdown, StateTransition types
```

---

## 4. Backend contract this frontend expects (FastAPI endpoints, no auth)

```
GET  /findings            ?sort=risk_score&order=desc&page=1 -> { items: Finding[], total }
GET  /findings/:id        -> Finding (includes risk_breakdown, state_transitions[])
GET  /repositories        -> Repository[]
POST /repositories        { url } -> Repository
GET  /metrics/mttr        ?days=30 -> { date, avg_mttr_hours }[]
GET  /metrics/summary     -> { total, critical, avg_mttr, verified_today }
```

No `Authorization` header, no 401 handling needed. If the backend later adds auth, only
`api/client.ts` needs to change (single interceptor point) — keep all other components
unaware of auth so that addition stays cheap.

---

## 5. What NOT to build

- No login/auth of any kind — single-user, trusted local/demo environment assumed
- No RBAC or multiple users
- No real-time websocket updates — poll `/findings` on a 30s interval instead; note
  websockets as a future enhancement
- No mobile-specific layout — responsive down to tablet width is enough for a capstone demo

---

## 6. Definition of Done

- [ ] Dashboard renders summary cards + sortable findings table from live/mocked API
- [ ] Finding detail page shows the risk score breakdown visually, not just a number
- [ ] Every table/list has a working empty state and loading skeleton (test by returning
  an empty array / delaying the mock response)
- [ ] Colorblind check: view the severity badges through a colorblind simulator
  (browser devtools emulation) and confirm they're still distinguishable
- [ ] No secret value ever appears in the rendered DOM or in any network response —
  inspect the network tab, not just the UI
- [ ] `README.md` in the frontend folder states explicitly: "No authentication — single-user
  local deployment. RBAC/multi-user auth is scoped as future work (see project report §11)."
