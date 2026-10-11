# Repository Guidelines

## Project Structure & Module Organization

`eventman_server.py` implements the Tornado server and REST API; `monco.py` handles MongoDB access, and `utils.py` provides shared utilities. The active frontend consists of `angular_app/index.html`, `angular_app/js/modern-app.js`, and `static/css/eventman-modern.css`. Other AngularJS sources are retired; avoid feature work there.

`tools/` contains scanner and database utilities. `data/triggers-available/` holds example triggers; enable them under `data/triggers/<action>.d/`. Consult `docs/DEVELOPMENT.md`, `docs/DOCKER.md`, and `docs/DEPENDENCIES.md`. No automated test suite currently exists.

## Build, Test, and Development Commands

Run from the repository root with Python 3.10+:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
./eventman_server.py --debug
```

Local execution requires a running MongoDB server. Open `http://localhost:5242/`.

- `docker compose up --build`: build and start EventMan with MongoDB.
- `docker compose config --quiet`: validate Compose configuration.
- `python -m compileall -q eventman_server.py monco.py utils.py tools data/triggers-available`: check Python compilation.
- `node --check angular_app/js/modern-app.js`: check JavaScript syntax; Node is only needed for this check.
- `git diff --check`: detect whitespace errors.

Install optional features through `requirements-eventbrite.txt`, `requirements-scanner.txt`, or `requirements-printing.txt`. There is no frontend build step or supported `pip install .` workflow.

## Coding Style & Naming Conventions

Use four spaces; Python indentation is mandatory. Follow existing Python `snake_case` and JavaScript `camelCase` conventions. Use Sphinx-style Python docstrings and preserve surrounding HTML/CSS style. No formatter or linter is configured.

## Testing Guidelines

Run the checks above and exercise changed API/UI behavior against a disposable database. For frontend changes, verify navigation, forms, and responsive rendering. No testing framework or coverage threshold is configured. If adding tests, use descriptive `test_*.py` names and document their execution command. Avoid triggering printers or scanners during routine validation.

## Commit & Pull Request Guidelines

History uses short, imperative summaries such as `add link to events on tickets`; no conventional-commit prefix is required. Keep changes focused. PRs should explain behavior, validation, relevant issues, and configuration changes; include screenshots for visible UI changes.

## Dependency & Configuration Boundaries

Keep external libraries and fonts outside the source tree. Declare Python dependencies in requirement files; keep the frontend dependency-free. Never commit credentials or SSL keys. Label printing requires external font paths documented in `docs/DEPENDENCIES.md`.

## Code Discovery

If `.codegraph/` exists, use `codegraph explore "<symbol or question>"` or the CodeGraph MCP tool before text searches or source reads. Otherwise, use `rg`.
