# Evaluation: Project Structure & Organization

| Field | Value |
|-------|-------|
| **Evaluated** | Full project directory structure |
| **Against** | Standard project organization practices |
| **Date** | 2026-04-27 |
| **Overall Grade** | 6 / 11 claims passed (55%) |

## Scorecard

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | .env not tracked in git | ❌ FAIL | `git ls-files .env` → TRACKED. API keys in version control. |
| 2 | .gitignore is comprehensive | ❌ FAIL | Only 11 lines. Missing: node_modules/, .DS_Store, .cursor/, dist/, *.egg-info tracked |
| 3 | No duplicate node_modules | ❌ FAIL | Root `node_modules/` exists alongside `frontend/node_modules/` |
| 4 | Backend structure is clean | ✅ PASS | Clean layered architecture: agents/job/{repos,services,prompts} + shared/{llm,algorithms,export,scraping} |
| 5 | Frontend structure is clean | ✅ PASS | Components, pages, api, tabs, ui — well organized |
| 6 | Tests mirror source structure | ✅ PASS | tests/agents/job/{repos,services} + tests/shared/{algorithms,export,llm,scraping} |
| 7 | Documentation is organized | 🟡 PARTIAL | v1 and v2 docs coexist with no clear "current". Reports have UUID hashes in names. |
| 8 | No orphaned/generated files tracked | ❌ FAIL | `backend/house_helper.egg-info/`, `backend/templates/README.md` |
| 9 | Scripts are organized | 🟡 PARTIAL | 5 shell + 2 bat scripts scattered at root. Functional but messy. |
| 10 | Config files in right places | ✅ PASS | pyproject.toml at root, frontend config in frontend/ |
| 11 | Root-level files are minimal | ✅ PASS | README, setup, test scripts — reasonable for project root |

## Critical Issues

### 1. `.env` tracked in git (SECURITY)
```
$ git ls-files .env
.env   ← TRACKED despite being in .gitignore
```
Contains ANTHROPIC_API_KEY, OPENAI_API_KEY, RAPIDAPI_KEY. If this repo was ever pushed to public, keys are compromised.

### 2. Root-level `node_modules/`
Exists at project root (probably from an accidental `npm install` outside frontend/). Adds confusion and ~100MB of unnecessary files.

### 3. `.gitignore` gaps
Missing: `node_modules/`, `.DS_Store`, `.cursor/`, `dist/`, `*.egg-info/` (the pattern has trailing slash issues)

### 4. Documentation clutter
- `pick_plan.md` at root — unclear purpose
- `DECISIONS.md` gitignored but exists
- v1 docs (`architecture/job-agent.md`, `requirements/job-agent.md`) are superseded by v2 but still present
- `reports/` has auto-generated files with UUID hashes — not human-readable names

## Recommendations

1. **Immediately:** `git rm --cached .env` + rotate API keys
2. **Clean .gitignore:** Add node_modules/, .DS_Store, .cursor/, dist/
3. **Remove root node_modules:** `rm -rf node_modules/` at project root
4. **Archive v1 docs:** Move to `docs/archive/` or delete
5. **Clean orphans:** Remove `backend/house_helper.egg-info/`, `backend/templates/`
6. **Move scripts:** `scripts/` directory or keep at root (minor)
7. **Rename reports:** Human-readable names instead of UUID hashes
