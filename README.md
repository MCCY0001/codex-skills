# codex-skills

Personal Codex skills source repository.

## Model

- Source of truth: `C:\Dev\codex-skills`
- Runtime directory: `C:\Users\mccy0\.codex\skills`
- Only edit personal skills in this repo
- Publish skills into the runtime directory with `scripts/publish_skills.ps1`
- Do not version `.system`

## Layout

- `skills/<skill-name>/...`: skill source
- `scripts/publish_skills.ps1`: publish selected or all personal skills

## Publish

Publish all personal skills:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_skills.ps1
```

Publish one skill:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_skills.ps1 -SkillName commit-segmenter
```

## Versioning

- Commit all skill source files
- Ignore caches and generated Python artifacts
- Tag only validated stable versions
