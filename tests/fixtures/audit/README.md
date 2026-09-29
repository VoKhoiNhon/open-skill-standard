# Audit test fixtures (test data)

These folders are inert test data for `open-skill audit`. They are not skills to install or run.

- `clean-skill/` is an ordinary skill; the audit must report nothing for it.
- `risky-skill/` contains text that imitates malicious skills so each audit rule has a real file to match. Every script starts with `exit 0`, every host uses the reserved `.invalid` domain, and no line is meant to be followed by a person or an agent.
