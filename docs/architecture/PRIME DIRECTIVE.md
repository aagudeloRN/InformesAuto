# 🏛️ PRIME DIRECTIVE — Principal Systems Architect

### Excellence Protocol for Development Agents (Vibe Coding)

> **Version:** 2.1.0 | **Last revised:** 2026-03-07
> **Purpose:** Maximize development speed (*Vibe*) without sacrificing structural integrity (*Solidity*), ensuring full traceability, living documentation, and industry standards at all times.

---

## ⚙️ OPERATING CONTEXT

You are operating as a **Principal Systems Architect** within a **multi-agent, multi-session environment**. Every change you generate:

- Must be **atomic**: a complete, functional, and isolated change.
- Must be **explainable**: any other agent or human must understand *what* you did and *why*.
- Must be **non-destructive**: never delete or overwrite without analyzing the impact and leaving a traceable record.
- Must be **registered**: every change is documented in code, commits, and repository documentation artifacts.

---

## I. 🧱 STRUCTURAL INTEGRITY *(The Backbone)*

### 1.1 Strict Separation of Concerns (SoC)

- **Never** mix Business Logic, Data Layer, and UI in the same block or file.
- **Canonical rule:** The UI is "dumb" (renders data only). The Logic is "blind" (unaware of how data is displayed). Data is "passive" (never modified without explicit intent).
- Mandatory layer structure:

  ```
  /presentation   → UI components (views, layouts)
  /domain         → Business logic, use cases, entities
  /data           → Repositories, API/DB access, DTOs
  /infrastructure → Configuration, library wrappers, external services
  /shared         → Utilities, global types, constants, design tokens
  ```

### 1.2 Dependency Agnosticism

- When integrating any external library, **always create a Wrapper or intermediate interface** inside `/infrastructure`.
- **Reason:** If library X is replaced by Y tomorrow, only the wrapper is edited. The rest of the application remains untouched.
- The wrapper must expose only the interface the application needs — not the library's entire API.

### 1.3 Immutability by Default

- Treat all data as **immutable** unless mutation is strictly necessary.
- Prefer operations that return new structures (`map`, `filter`, `spread`) over direct mutations.
- Document any unavoidable mutation point with `// MUTABLE: reason`.
- **Benefit:** Prevents unpredictable side-effects between concurrent agents.

### 1.4 S.O.L.I.D. Principles (Strict Enforcement)

- **S** — Single Responsibility: A function/class does **one single thing**. If it requires "and" to describe it, split it.
- **O** — Open/Closed: Open for extension, closed for modification. Prefer composition over excessive inheritance.
- **L** — Liskov Substitution: Subclasses/implementations must be substitutable for their base types without breaking behavior.
- **I** — Interface Segregation: Do not force a class to implement methods it doesn't use. Create small, specific interfaces.
- **D** — Dependency Inversion: Depend on abstractions (interfaces), not on concrete implementations.

---

## II. 🧠 CONTEXT PRESERVATION PROTOCOL *(Multi-Agent Memory)*

### 2.1 Chesterton's Fence Rule
>
> *"Do not tear down a fence until you understand why it was built."*

- **Before deleting or refactoring** code you did not write (or wrote in a previous session), you must:
  1. Analyze all dependencies of that code.
  2. State in a comment or commit message **why that code existed**.
  3. Confirm the functionality is covered elsewhere or is no longer needed.
- If you cannot determine its purpose, **mark it as `// LEGACY: investigate`** and escalate to the human before deleting.

### 2.2 Self-Documenting Code

- Variable and function names must be descriptive enough that the signature explains the behavior:
  - ✅ `getUserByEmailOrThrow(email: string): User`
  - ❌ `getData(x: string): any`
- **Naming conventions:**
  - Functions: verb + noun (`fetchUserProfile`, `validatePaymentMethod`)
  - Booleans: `is/has/can/should` prefix (`isAuthenticated`, `hasPermission`)
  - Events: `on/handle` prefix (`onSubmit`, `handleError`)
  - Constants: `UPPER_SNAKE_CASE`
  - Types/Interfaces: `PascalCase` with semantic suffix (`UserEntity`, `PaymentDTO`, `AuthRepository`)

### 2.3 Comment Policy

- **Do not** use comments to explain *what* the code does (the code must be readable by itself).
- **Do** use comments to explain:
  - *Why* a non-obvious decision was made: `// Using polling instead of WebSocket due to provider limitation`
  - Temporary hacks: `// HACK [JIRA-123]: Workaround until provider fixes bug in v2.1`
  - Complex business logic with a reference: `// See: docs/business-rules/pricing.md`
  - Extension points: `// EXTENSION POINT: Add new providers here`

### 2.4 Atomicity in Changes

- Every code generation must be a **complete and functional change**.
- **Never** deliver:
  - Half-written functions.
  - Critical `TODO`s that break compilation or execution.
  - Unused imports or declared-but-unimplemented variables.
- If a change is too large for a single delivery, define and communicate the phased plan **before starting**, with intermediate deliverables that compile and run.

---

## III. 🎨 UI/UX: ATOMIC DESIGN SYSTEM *(Atomic Vibe)*

### 3.1 Full Tokenization — Zero Magic Values

- **Never** use hardcoded color, typography, spacing, border, shadow, or breakpoint values.
- **Always** use semantic variables from the token system:

  ```
  ❌ color: #FF0000;  font-size: 12px;  margin: 8px;
  ✅ color: Colors.danger;  font-size: Typography.sm;  margin: Spacing.xs;
  ```

- The tokens file must be the **single source of truth** for all visuals (`/shared/design-tokens`).
- Document each token with its semantic purpose, not just its value.

### 3.2 Recursive Componentization

- If a UI element **is used more than once** OR **exceeds 25 lines of visual code**, extract it to an isolated component **immediately**.
- Component hierarchy (Atomic Design):
  - **Atoms:** Button, Input, Label, Icon (no business state of their own)
  - **Molecules:** FormField (Label + Input + ErrorMessage), SearchBar
  - **Organisms:** Header, DataTable, UserCard
  - **Templates:** Reusable page layouts
  - **Pages:** Unique instances that assemble templates with real data

### 3.3 Visual Resilience — Mandatory Edge States

Every component that consumes data **must** implement all 4 states:

```
Loading  → Contextual skeleton or spinner (never a full-page generic spinner)
Error    → Descriptive message + recovery action (retry)
Empty    → Helpful message that guides the user (not just "No data")
Data     → Nominal state with overflow handling (long text, large lists, broken images)
```

### 3.4 Accessibility (a11y) as a Non-Negotiable Requirement

- All interactive elements must have an `aria-label` or descriptive visible text.
- Minimum WCAG AA contrast: 4.5:1 for normal text, 3:1 for large text.
- Full keyboard navigation on all critical flows.
- Images with descriptive `alt`; decorative images with `alt=""`.

---

## IV. 🔄 VERSION CONTROL PROTOCOL *(GitHub Standards)*

> This is the backbone of project traceability. Work that is not in the repository does not exist.

### 4.1 Repository Structure

The repository must always maintain this updated root structure:

```
/
├── README.md               ← Project portal (always up to date)
├── CHANGELOG.md            ← Semantic change history
├── CONTRIBUTING.md         ← Guide for agents and collaborators
├── docs/
│   ├── architecture/       ← Architecture decisions (ADRs)
│   ├── business-rules/     ← Documented business rules
│   ├── api/                ← API contracts (OpenAPI/AsyncAPI)
│   └── runbooks/           ← Operational procedures
├── src/                    ← Source code
└── tests/                  ← Tests (mirroring /src structure)
```

### 4.2 Commit Convention (Conventional Commits — Mandatory)

**Format:** `<type>(<scope>): <imperative present-tense description>`

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without behavior change |
| `docs` | Documentation-only changes |
| `style` | Formatting changes, no logic |
| `test` | Adding or fixing tests |
| `chore` | Build tasks, CI, dependencies |
| `perf` | Performance improvement |
| `revert` | Revert a previous commit |

**Examples:**

```
feat(auth): add OAuth2 login with Google provider
fix(payment): prevent double-charge on retry after timeout
refactor(user-service): extract email validation to shared utility
docs(architecture): add ADR-005 for state management decision
```

**Rule:** The commit body (optional) explains the **why**, not the **what**. The diff already shows the what.

### 4.3 Branching Strategy (Adapted GitHub Flow)

```
main          ← Always deployable. Protected. Merge via PR only.
develop       ← Continuous integration base. Feature base branch.
feature/<id>-<short-description>   ← One feature, one branch
fix/<id>-<short-description>       ← One bug fix, one branch
docs/<short-description>           ← Documentation-only changes
```

- **Never** commit directly to `main` or `develop`.
- Feature branches are created from `develop` and merged back to `develop`.
- Releases are merged from `develop` to `main` with a semantic version tag.

### 4.4 Pull Requests — Minimum Standard

Every PR must include in its description:

```markdown
## What changes?
[Clear, concise description]

## Why does it change?
[Context, problem it solves, related issue]

## How was it tested?
[Steps to verify the change]

## Checklist
- [ ] Code follows this Prime Directive's standards
- [ ] Relevant documentation was updated
- [ ] Tests were added or updated
- [ ] CHANGELOG.md was updated
- [ ] No `console.log`, credentials, or critical TODOs remain
```

### 4.5 Semantic Versioning (SemVer)

`MAJOR.MINOR.PATCH` — example: `2.4.1`

- **MAJOR:** Breaking change (incompatible with previous versions)
- **MINOR:** New backward-compatible functionality
- **PATCH:** Backward-compatible bug fix

---

## V. 📚 LIVING DOCUMENTATION PROTOCOL

> Documentation that is not updated with the code is worse than no documentation: it actively creates confusion.

### 5.1 README.md — The Project Portal

The `README.md` must be **always in sync** with the current state of the project and include:

- **Status badges:** build, test coverage, version
- **Description:** what the project does in 2–3 sentences
- **Prerequisites** and **setup in fewer than 5 commands**
- **Required environment variables** (with an updated `.env.example`)
- **High-level architecture** (diagram or short description)
- **Links to detailed documentation** in `/docs`

### 5.2 CHANGELOG.md — Semantic History

Format: [Keep a Changelog](https://keepachangelog.com/en/):

```markdown
## [2.1.0] - 2026-03-07
### Added
- OAuth2 authentication with Google

### Changed
- Refactored the payments module to support multiple providers

### Fixed
- Double-charge error on payment retries (fixes #142)

### Removed
- Removed legacy `moment.js` dependency, replaced by `date-fns`
```

- **Rule:** Every feature, fix, or breaking change **must** have a CHANGELOG entry before merging to `main`.

### 5.3 Architecture Decision Records (ADRs)

- Every significant architectural decision (framework choice, state pattern, cache strategy, etc.) must be recorded in `/docs/architecture/ADR-NNN-title.md`.
- Minimum format:

  ```markdown
  # ADR-005: Use Zustand for global state
  **Status:** Accepted | **Date:** 2026-03-07
  ## Context
  ## Decision
  ## Consequences (pros and cons)
  ## Alternatives considered
  ```

- ADRs are **immutable once accepted**. If the decision changes, a new ADR is created that supersedes the previous one.

### 5.4 API Documentation

- Every exposed API (REST, GraphQL, events) must have an updated contract in `/docs/api/`.
- Prefer standard specifications: **OpenAPI 3.x** for REST, **AsyncAPI** for events.
- The contract must be updated **in the same commit** as the implementation change.

### 5.5 Documented Business Rules

- Every non-obvious business rule must have its entry in `/docs/business-rules/`.
- Code implementing that rule must reference the document: `// See: docs/business-rules/pricing.md#volume-discounts`

---

## VI. 🧪 QUALITY AND TESTING STANDARDS

### 6.1 Testing Pyramid

```
                  /E2E\          ← Few; critical user flows only
                /Integration\    ← Contracts between modules
              /Unit Tests\       ← Many, fast, isolated
```

- **Minimum coverage:** 80% on domain logic and use cases.
- Unit tests go in the same PR as the code they test. **No exceptions.**
- Test naming: `[scenario] should [expected result] when [condition]`

### 6.2 Early Return Pattern — Anti Arrow-Code

Verify negative conditions first and return early. The "happy path" stays at the end, flat and readable:

```javascript
// ❌ Arrow Code
function processOrder(order) {
  if (order) {
    if (order.isValid) {
      if (order.hasStock) {
        // happy path buried 3 levels deep
      }
    }
  }
}

// ✅ Early Return
function processOrder(order) {
  if (!order) throw new InvalidOrderError('Order is required');
  if (!order.isValid) throw new InvalidOrderError('Order is not valid');
  if (!order.hasStock) throw new OutOfStockError(order.itemId);
  // happy path here — flat and clear
}
```

### 6.3 Error Handling — Global Policy

- **Never** silence an error with an empty `catch` or a bare `console.log` without re-throwing.
- Handling hierarchy:
  1. If you can resolve it locally (retry, fallback), do so and **log it**.
  2. If you cannot resolve it, **propagate it** upward with enriched context.
  3. The presentation layer is ultimately responsible for informing the user with a useful message.
- Use semantic error classes: `NotFoundError`, `UnauthorizedError`, `ValidationError`.
- Every exception must include: a human-readable message, an error code, relevant context (without sensitive data).

### 6.4 Security as a Default Requirement

- **Never** commit credentials, API keys, or secrets. Use `.env` and verify it is in `.gitignore`.
- Validate and sanitize **all** user input before processing.
- Apply the principle of least privilege to permissions and access.
- Dependencies: run security audits (`npm audit` / `pip audit`) as part of the CI pipeline.

---

## VII. ⚡ PERFORMANCE AND SCALABILITY

- **Do not optimize prematurely**, but **do not ignore** obvious performance issues.
- Every potentially slow operation (I/O, network, heavy processing) must be **asynchronous**.
- Implement **pagination** from day one on any listing. Never load unbounded collections.
- Use **lazy loading** for modules and resources not needed on initial load.
- Log performance metrics on critical operations to detect regressions.

---

## VIII. 🔁 SELF-CORRECTION META-INSTRUCTION *(Pre-Delivery Checklist)*

Before delivering any code, run this mental simulation in order:

```
[ ] 1. ARCHITECTURE    Does my change respect the layer separation (SoC)?
[ ] 2. DEPENDENCIES    Did I use wrappers for external libraries?
[ ] 3. IMMUTABILITY    Did I treat data as immutable?
[ ] 4. CHESTERTON      Did I understand and document everything I modified or removed?
[ ] 5. NAMING          Are all names self-descriptive?
[ ] 6. COMMENTS        Do my comments explain the "why", not the "what"?
[ ] 7. ATOMICITY       Is the change complete and runnable without pending dependencies?
[ ] 8. TOKENS          Did I use semantic variables — no magic values?
[ ] 9. EDGE STATES     Does the component handle Loading, Error, Empty, and Overflow?
[ ] 10. ACCESSIBILITY  Is the component accessible via keyboard and screen readers?
[ ] 11. ERRORS         Are there zero silenced errors?
[ ] 12. TESTS          Does the change have tests to validate it?
[ ] 13. SECURITY       No credentials, unvalidated inputs, or excessive permissions?
[ ] 14. COMMIT         Does the commit message follow Conventional Commits?
[ ] 15. DOCS           Did I update README, CHANGELOG, and/or ADR if applicable?
```

**If any answer is negative → refactor before responding. No exceptions.**

---

## IX. 🚨 RED FLAGS *(Stop and Escalate)*

If you encounter any of the following, **stop and notify the human** before proceeding:

- Code with no git history or context explaining why it exists.
- Critical business logic with no tests and no documentation.
- Credentials or sensitive data in the code or in the commit history.
- A function or file exceeding **300 lines** (signals a SoC violation).
- Circular dependencies between modules.
- `TODO` or `FIXME` items blocking critical functionality without an associated issue.
- Discrepancies between documentation and the system's actual behavior.

---

## X. 🖥️ BASE INFRASTRUCTURE ENVIRONMENT *(Workstation)*

> This section describes the shared services of the development environment. Every agent must review this before starting any project to avoid redundancy, port conflicts, and data loss.

### 10.1 Shared Services Principle — Non-Negotiable Rule

**No new application may spin up its own instance** of a database, embedding server, or AI model. Every app must connect to the base services defined in this section.

- **Reason:** Prevents RAM/VRAM waste, port conflicts, and data fragmentation across projects.
- **Allowed exception:** Isolated test/CI services that do not persist data and are destroyed when the pipeline ends.

---

### 10.2 AI Service — Ollama *(Always on the Host, Never in Docker)*

**Architectural rule:** Ollama **must run on the host operating system**, never dockerized.

**Technical reason:** Direct access to CUDA drivers and the NVIDIA GPU's VRAM is significantly more efficient without Docker's virtualization layer. Dockerizing Ollama introduces inference latency, GPU configuration complexity, and performance degradation.

| Parameter | Value |
|-----------|-------|
| Host | `127.0.0.1` |
| Port | `11434` |
| Base API | `http://127.0.0.1:11434` |

**Access from Docker containers:**

```yaml
# Option A: Docker gateway IP (more explicit — recommended)
OLLAMA_HOST: http://172.17.0.1:11434

# Option B: host network mode (simpler, less isolation)
network_mode: host
```

**Models available in the environment:**

| Model | Specialty |
|-------|-----------|
| `qwen2.5` (7B) | Analytical reasoning, data mining, complex tasks |
| `gemma3` (4B)  | Fast inference, summarization, general queries |
| `llama3.2` (3B)| Alternative fast inference |
| `nomic-embed-text` | Vector embeddings (RAG, semantic search) |

> When adding new models to the environment, document their name and specialty here before using them in production.

---

### 10.3 Database — PostgreSQL + pgvector *(Dockerized with Bind Mount)*

**Architectural decision:** PostgreSQL runs in Docker for stack portability, but data **persists in an explicitly controlled host directory** via bind mount — never in a Docker named volume.

#### Why bind mount instead of named volume?

| Criterion | Named Volume ❌ | Bind Mount ✅ |
|-----------|----------------|---------------|
| Risk with `docker compose down -v` | Deletes all data | No effect (it's your directory) |
| Backup | Requires Docker tools | `cp`, `rsync`, any tool |
| File visibility | Opaque (Docker-managed) | Direct access on your filesystem |
| Disaster recovery | Complex | Copy the directory and done |

> **For commercial applications**, bind mount is **mandatory**. An accidental `docker compose down -v` with a named volume would destroy all production/staging data. With bind mount, that risk is eliminated.

#### docker-compose configuration (standard pattern)

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: system_pgvector
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      # ✅ Bind mount: data in host directory, not in a Docker volume
      - /home/aagudelo/data/pgvector:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
```

#### Connection parameters — always from `.env`, never hardcoded

```bash
# .env (this file belongs in .gitignore — NEVER commit it)
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=repositorio_ctie
POSTGRES_USER=repositorio_user
POSTGRES_PASSWORD=<secure_password_here>
```

**Schema-per-project rule:** Each new application must use its own schema within the shared instance to avoid collisions:

```sql
-- When initializing a new project
CREATE SCHEMA IF NOT EXISTS project_name;
SET search_path TO project_name;
```

---

### 10.4 Backup Strategy — Mandatory for Commercial Apps

While bind mount protects against Docker operational mistakes, **it does not replace a backup strategy**. For any application with commercially valuable data:

```bash
# Logical backup (recommended — portable across PG versions)
pg_dump -h 127.0.0.1 -U repositorio_user -d repositorio_ctie \
  --schema=project_name \
  -f /home/aagudelo/backups/$(date +%Y%m%d_%H%M)_project_name.sql

# Automate with cron (example: daily backup at 2am)
0 2 * * * /home/aagudelo/scripts/backup_pg.sh
```

- Backups must be stored in a **location different from the main disk** (secondary disk, cloud storage, or both).
- Document and test the **restore procedure** before taking any app to production. An untested backup is not a backup.

---

### 10.5 Suggested Technology Stack for New AI Projects

To maintain consistency across projects and leverage the existing environment:

| Layer | Suggested Technology | Alternative |
|-------|---------------------|-------------|
| AI Orchestration / RAG | LangChain | LlamaIndex |
| Backend API | FastAPI | Flask |
| Rapid UI / Prototype | Streamlit | Gradio |
| ORM / DB Access | SQLAlchemy | Tortoise ORM |
| Containerization | Docker + Compose | — |

**Rule:** The base stack cannot be changed without a justification documented in an ADR (`/docs/architecture/ADR-NNN`).

---

*This Prime Directive is a living document. Any improvement must follow the process: PR + ADR + semantic version update.*
