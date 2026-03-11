# Conventional Commits

Default spec for `commit-segmenter`.

## Commit format
- `type(scope): description`
- `type: description`

## Allowed types
- `feat`
- `fix`
- `docs`
- `refactor`
- `test`
- `chore`
- `build`
- `ci`
- `revert`

## Scope rules
- `docs,documentation,design -> docs`
- `scripts -> scripts`
- `tests,testing,test -> tests`
- `tooling,tools -> tooling`
- `src,source,packages,pkg -> src`
- `infra,infrastructure -> infra`
- `config,configs -> config`
- `assets -> assets`
- `artifact,artifacts,plots,runs -> artifacts`
- `ci -> ci`

## Fallback scope
- commit type

## Ignore patterns
- `.git`
- `.idea`
- `.vscode`
- `.mypy_cache`
- `.pytest_cache`
- `__pycache__`
- `.venv`
- `venv`
- `build`
- `dist`
- `node_modules`
