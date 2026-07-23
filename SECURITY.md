# Security Policy

## Supported versions

Only the `1.x` line (the native Qt Quick / PySide6 rewrite) is supported.
Releases before `1.0.0` predate the rewrite and will not receive security
fixes.

## Reporting a vulnerability

**Do not open a public issue.** Report privately via [GitHub Security
Advisories](https://github.com/I4cTime/protonshift/security/advisories/new).
This is the same flow linked from the issue template and the security
contact link on this repo.

Include what ProtonShift version (or commit hash) you're on, your
distribution, and reproduction steps.

## Response expectations

ProtonShift is a single-maintainer, unfunded project. Reports are handled
best-effort — there's no SLA. You should get an acknowledgment and, if the
report is valid, a fix or mitigation timeline.

## Scope

ProtonShift is a native desktop app: no HTTP server, no Electron, no remote
attack surface by design. The security-relevant code paths are:

- **Filesystem writes to game/tool config** (`MangoHud.conf`, `scb.conf`,
  Heroic per-game JSON, Steam launch options, save backups, and the known-
  fixes DB) — path and filename handling for these goes through
  `protonshift/core/paths.py`, which rejects `..`/absolute/null-byte escapes
  and constrains writes to expected roots. A bypass here that lets untrusted
  input write or delete outside those roots is a security issue.
- **Host command execution.** Inside the Flatpak sandbox, `core/host.py`
  routes host tool calls (`nvidia-smi`, `gamescope`, `protontricks`,
  `xrandr`, etc.) through `flatpak-spawn --host`. Anything that lets
  untrusted input reach these calls unsanitized — including `scb.conf`,
  which is bash-sourced at game launch — is a security issue.

Bugs outside this scope (a game misbehaving, a UI glitch) are regular bug
reports — use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml)
instead.
