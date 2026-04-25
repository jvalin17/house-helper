# Skills Feedback — Lessons from house-helper

> Maintained based on real experience building the job-agent.
> These are generalized improvements for agent-toolkit skills.

## /requirements

1. **File operations must specify UX pattern.** When a capability says "import file" or "upload," require: drag-and-drop, file picker, paste, or clipboard. Default to drag-and-drop + file picker. We shipped a text input for file paths — unusable.

2. **Trace the core flow for priority validation.** "Resume import" was marked "should" but the app was broken without it (can't generate resume from empty knowledge bank). Any capability on the critical user path must be "must."

3. **Multi-input features need explicit modes.** "Add a job" actually means: paste URL, paste text, drag-and-drop file, or type. Each mode needs its own spec line. Don't collapse them into one row.

4. **Requirements drift tracking.** We added 5 major features during architecture (multi-LLM, offline, calibration, JSON-LD, Sentence Transformers) that were never formally in requirements. Skill should detect drift and prompt to formalize.

## /architecture

5. **Always include minimal frontend architecture when UI is in scope.** We designed 15 backend decisions but said "frontend: decide later." Result: no component hierarchy, no state management plan, inconsistent page structure.

6. **Threading/concurrency must be addressed for every DB + framework combo.** SQLite + FastAPI worker threads crashed the app. This is a known issue the architecture should flag automatically.

7. **Primary user flow diagram is mandatory.** Not just data flow — the actual user journey (open app → import resume → paste job → match → generate → preview → apply). This catches gaps like "what happens if knowledge bank is empty?"

## /implementation

8. **File uploads must use multipart + drag-and-drop, never file paths.** File paths are a dev shortcut. First implementation used `{"file_path": "/Users/..."}` — only works locally, terrible UX. Enforce: user-facing file input = multipart upload + drag-and-drop UI.

9. **At least one end-to-end integration test with real data.** We had 190+ unit tests but the first real URL crashed the app (parser didn't fetch URLs). Require one test that simulates the actual user journey.

10. **Check runtime version compatibility early.** Python 3.14 was too new for sentence-transformers and spaCy (15 tests skipped). Skill should check version against dependency requirements before writing code.

11. **Port management.** Default to non-standard port (8040 not 8000), make it configurable via env var. Two projects fighting for port 8000 blocked the user.

12. **Feature completeness on the page it belongs to.** Resume import UI was initially on the Knowledge Bank tab only, but users expect it on the main page too. The extracted data should flow to the right place (knowledge bank) while the action (upload) lives where users first land.

## /evaluate

13. **Add a smoke test step.** Evaluate checked files and structure but couldn't catch that the app crashes when you paste a URL, or that resume generation produces empty output. Starting the app and trying the primary action would catch these.

## General

14. **"Import" is always multi-modal.** Any import feature should support at minimum: drag-and-drop, file picker (browse button), and paste text. These are not three features — they're one feature with three entry points.

15. **Empty state handling.** Every "generate from data" feature needs an empty state check with a helpful message and action link. "Knowledge bank is empty → go import your resume" was missing until the user hit a blank preview.

16. **Resume/document parsing is a standalone, reusable module.** Don't couple it to any specific service. We built it in `shared/scraping/resume_parser.py` — it's used by the knowledge service, the import endpoint, and could be used by future agents.
