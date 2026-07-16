# Ani Book Skill

[中文](README.md) · [Changelog](docs/releases/release-notes.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Ani Book Skill is a Codex workflow for producing long-form Chinese web novels. It turns ideas, story planning, drafting, review, and continuity into editable, recoverable Markdown artifacts.

## Highlights

- Move from an idea to a novel brief, story bible, world, cast, volume plan, and chapters.
- Preserve long-form continuity with chapter contracts, context packages, and readable ledgers.
- Revise and review drafts while protecting accepted facts and author-written prose.
- Export completed chapters to TXT and check workspace continuity with included Python tools.
- Keep content local and portable with Markdown and YAML.

## Use it

Install this repository as a personal Codex Skill, then invoke it in Codex:

```text
Use $produce-long-form-novel to plan a long novel from my idea.
```

Read [SKILL.md](SKILL.md) for the complete workflow contract. The primary documentation is maintained in Chinese because the workflow targets Chinese fiction.

## Local tools

Python 3.10+ is required; no third-party packages are needed.

```powershell
python scripts/export_novel_txt.py novels/<novel-name>
python scripts/check_continuity_workspace.py novels/<novel-name>
```

`novels/` is ignored by default to protect private manuscripts. Put only authorized, sanitized examples in `examples/` if you choose to publish them.

## Contributing and license

Please read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md). This project is released under the [Apache License 2.0](LICENSE).
