# Contributing to KeyForge

## Welcome

Thanks for your interest in contributing to KeyForge. KeyForge is an open-source, self-hosted credential management platform, and it benefits from outside eyes on its code, docs, threat model, and developer ergonomics. Bug reports, feature pull requests, documentation fixes, and integration ideas are all welcome. This document covers what you need to know before opening a pull request: how to get a development environment running, how to name branches and commits, what tests need to pass, and the code style rules the project enforces.

## Development setup

The README's [5-minute quickstart](README.md#5-minute-quickstart) gets you a running stack. For everything else (bare-metal backend and frontend commands, formatter and linter invocations, end-to-end test setup, required environment variables, and project conventions), [CLAUDE.md](CLAUDE.md) at the repo root is the authoritative reference. Read it before making non-trivial changes; it documents architecture decisions and gotchas that are easy to violate by accident.

## Branching convention

Never commit to `main` directly. All changes land via pull request from a feature branch. Branch names use one of these prefixes:

- `feature/` for new functionality
- `fix/` for bug fixes
- `refactor/` for code restructuring with no behavior change
- `hotfix/` for urgent production patches

Example: `feature/github-issuer`, `fix/audit-hash-chain-off-by-one`, `refactor/split-models-by-domain`.

## Commit format

Commits use conventional-commit-style prefixes:

- `feat:` a new user-visible feature
- `fix:` a bug fix
- `chore:` maintenance, tooling, dependency bumps
- `docs:` documentation only
- `refactor:` code restructure with no behavior change
- `test:` adding or updating tests

Keep the subject line short (under 72 characters), use the body for the why, and reference relevant issues.

No `Co-Authored-By:` trailers on commits, ever. No `Generated with Claude Code` footers in PR bodies.

## Test policy

Every pull request must keep the backend test suite green:

```
python -m pytest tests/
```

New backend functions deserve unit tests. New API endpoints (anything added under `backend/routes/`) require integration tests that exercise the route through FastAPI's test client. Pull requests that change frontend code must build cleanly:

```
cd frontend
yarn build
```

If your change touches encryption, the audit log, or authentication, add tests that demonstrate the security property you intend to preserve. Those subsystems are load-bearing and changes there get the closest review.

## Code style

Backend code is formatted with `black` and `isort`, and linted with `flake8` using a 120-character line length:

```
python -m black backend/
python -m isort backend/
python -m flake8 backend/ --max-line-length=120 --ignore=E501,W503
```

Do not hand-wrap to 88 characters; the project line length is 120.

Frontend code uses CRACO (not vanilla react-scripts) and `eslint`:

```
cd frontend
npx eslint src/
```

Always invoke `yarn` scripts or `npx craco`, never `npx react-scripts` directly, or you bypass project overrides. The project uses React 19 and react-router-dom v7 data-router APIs in new code.

## Pull request review

Keep pull requests focused: one logical change per PR makes review tractable and bisects easier. Link related issues in the description. If your PR is large by necessity (a new subsystem, a refactor that touches many files), say so up front and offer a suggested review order. Expect feedback; security-sensitive changes will get more rounds of review than cosmetic ones.

## Security

Do not include real credentials in tests, fixtures, sample data, screenshots, documentation, or anywhere else in the repository. Use synthetic values only. Strings that look like keys but are obviously fake (for example, `sk_test_REDACTED_FOR_TESTS`) are fine; anything that could be a live secret is not. If you discover a security vulnerability in KeyForge, do not open a public issue. Report it through the process in the README's Security section.

## Code of Conduct

Contributors are expected to be respectful, constructive, and patient with each other. Disagreements about technical direction are normal and welcome; personal attacks, harassment, and discriminatory behavior are not. Maintainers will moderate accordingly.
