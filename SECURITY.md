# Security

## Reporting a vulnerability

Please report security issues privately through GitHub's **Report a vulnerability** button on the repository's Security tab (private vulnerability reporting). Do not open a public issue for security problems. You should receive a response within a week.

## Scope and design

- The CLI runs locally, reads skill folders and project file names, and writes only under `~/.open-skill/` (or `OPEN_SKILL_HOME`) and, for `build`, inside this repository.
- Project inspection never reads file contents.
- The user layer (`~/.open-skill/`: profile, knowledge notes, usage events) never leaves the machine unless the user runs `open-skill export`. CI blocks those files from being committed.
- `open-skill learn` refuses text that looks like credentials, tokens, emails or phone numbers unless forced.
- The router never runs project initialization or install commands; it only prints them.
- Skill content from third-party projects is not redistributed; install upstream skills from their own sources and review them before use, since skills run with the agent's permissions.
