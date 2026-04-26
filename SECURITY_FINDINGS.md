# SECURITY_FINDINGS.md

Tracker for known third-party vulnerabilities that are not yet fixed in the
KeyForge dependency pin set, with the conditions that would make a fix
possible. Updated as part of Tier 4.3 of `tasks/todo.md`.

## Outstanding (irreducible until upstream upgrade)

### starlette: CVE-2025-62727, CVE-2025-54121, CVE-2024-47874

- **Package:** `starlette`
- **Current pin:** `starlette==0.37.2`
- **Why pinned here:** `fastapi==0.110.1` (the version Tier 1.1 stabilised
  the test suite on) requires `starlette>=0.37.2,<0.38.0` internally, and a
  newer Starlette dropped the `on_startup` kwarg that FastAPI 0.110.1 still
  uses internally. Bumping starlette in isolation would re-break CI in the
  same way Tier 1.1 originally fixed.
- **Findings:**
  - `CVE-2025-62727` (PyUp 80876): DoS via inefficient Range header parsing.
    Fixed in starlette `>=0.49.1`.
  - `CVE-2025-54121` (PyUp 78279): Multipart parsing DoS. Fixed in starlette
    `>=0.47.2`.
  - `CVE-2024-47874` (PyUp 73725): Multipart DoS. Fixed in starlette
    `>=0.40.0`.
- **Mitigations in place:**
  - Sanitization middleware (`backend/middleware/sanitizer.py`) and
    rate-limit middleware (`backend/middleware/rate_limiter.py`) sit in
    front of the affected Starlette code paths.
  - File uploads are not exposed publicly; all inbound traffic is intended
    to be reverse-proxied behind a hardened nginx/CDN layer per the
    deployment guide.
- **Condition to safely upgrade:** Bump `fastapi` to `>=0.115` (which
  declares `starlette>=0.40`) and `>=0.131` for the strictest remediation,
  re-run the full pytest suite (currently 443 tests), and confirm that the
  `lifespan` handler in `backend/server.py` plus every router we own still
  load. This is a coordinated upgrade that belongs in its own task, not in
  Tier 4.3 security follow-ups.
- **Tracking:** Open follow-up task to land a coordinated FastAPI bump.

## Resolved during Tier 4.3

### python-multipart: CVE-2024-53981, CVE-2026-24486 (and friends)

- Was `python-multipart>=0.0.6` (unpinned in safety's view, version 0.0.24
  installed locally). Tightened to `python-multipart>=0.0.22` so safety
  recognises the fixed range and so a future fresh install cannot
  inadvertently resolve to a pre-0.0.22 version.

## Bandit findings

All bandit `-l --skip B101` findings were triaged during Tier 4.3 and either
fixed or annotated with a precise `# nosec B###  # reason: ...` comment in
the source. No bandit findings remain unsuppressed at `-l` (low) severity
or above. See the Tier 4.3 entry in `tasks/todo.md` for the per-file list.
