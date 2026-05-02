# Merge Notes: feature/nestscout-skeleton → main

## Files modified on both branches (potential conflicts)

| File | Branch Change | Resolution |
|------|--------------|------------|
| `frontend/src/api/client.ts` | Added NestScout API methods at end of `api` object | **Keep both** — NestScout methods are appended, no overlap with Jobsmith methods |
| `frontend/src/App.tsx` | Added `/apartments` route + ApartmentDashboard import | **Keep both** — one new import + one new Route line |
| `frontend/src/pages/Home.tsx` | Changed NestScout card from "Coming soon" to "Active" | **Take branch** — NestScout is now ready |
| `frontend/src/test/pages.test.tsx` | Updated test for NestScout active status | **Take branch** |
| `backend/shared/db.py` | Added migration v5 (7 apartment tables) | **Keep both** — migration appended to MIGRATIONS list |
| `backend/coordinator.py` | Added apartment agent import + registration | **Keep both** — one import + one line in _register_agents |
| `backend/main.py` | Updated health endpoint agents list | **Take branch** — includes both agents |

## New files (no conflicts)

All files under these directories are new — no conflict possible:
- `backend/agents/apartment/` (entire directory)
- `backend/shared/url_fetcher.py`
- `backend/shared/app_logger.py`
- `frontend/src/pages/ApartmentDashboard.tsx`
- `frontend/src/components/apartment/` (entire directory)
- `tests/agents/apartment/` (entire directory)
- `tests/shared/test_url_fetcher.py`

## Merge command

```bash
git checkout main
git merge feature/nestscout-skeleton
# If conflicts: use this file as guide
# Then: python -m pytest tests/ && cd frontend && npx vitest run
```
