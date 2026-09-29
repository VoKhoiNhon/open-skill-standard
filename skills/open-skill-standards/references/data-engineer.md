<!-- Generated from registry/roles/data-engineer.yaml by `open-skill build`. Edit the YAML, not this file. -->

### Data Engineer principles

Merge into `.specify/memory/constitution.md` for projects where this role leads.

- **Loads are idempotent**: re-running a date range never duplicates data.
- **Every run is reconciled against its source (row counts, key totals).**
- **Schema changes are declared and downstream consumers are checked.**
- **No personal data in logs, repositories or prompts.**
- **Shared tables have a data contract (ODCS).**
