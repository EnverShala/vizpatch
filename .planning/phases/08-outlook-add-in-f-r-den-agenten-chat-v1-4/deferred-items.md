# Deferred Items — Phase 8

Out-of-scope discoveries logged during plan execution (not fixed — see scope
boundary rule in the executor workflow).

## ROADMAP.md: stale "1/4 plans executed" line for Phase 7 (pre-existing)

- **Found during:** 08-02 execution, while restoring a similarly-corrupted line for Phase 8 (see 08-02-SUMMARY.md "Issues Encountered")
- **Location:** `.planning/ROADMAP.md`, Phase 7 section (`### Phase 7: Agenten-Chat im WebUI (v1.3)`), the `**Plans:**` summary line
- **Issue:** The line reads `**Plans:** 1/4 plans executed`, but Phase 7 is fully complete (4/4 plans, all committed 2026-07-17 per STATE.md history). This value was already present in `HEAD` before 08-02 execution started — it was NOT introduced by this plan's execution. Root cause is almost certainly a prior `roadmap.update-plan-progress` SDK call (from 08-01 or earlier) whose `summary_count` computation undercounted existing SUMMARY.md files for that phase.
- **Why deferred:** Out of scope for 08-02 (only Phase 8 files were touched by this plan). Fixing it would touch a section this plan has no mandate over.
- **Suggested fix:** Re-run `gsd-sdk query roadmap.update-plan-progress 7` (or manually restore the descriptive wave-breakdown text) during the next plan/phase that legitimately touches Phase 7's ROADMAP.md section, or as a standalone maintenance task.
