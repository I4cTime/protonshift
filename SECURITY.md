# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please report them privately using one of the following methods:

### 1. GitHub Private Vulnerability Reporting (preferred)

Use GitHub's built-in private reporting:

**[Report a vulnerability](https://github.com/I4cTime/protonshift/security/advisories/new)**

### 2. Email

Send details to the maintainer directly. You can find contact information on the [@I4cTime GitHub profile](https://github.com/I4cTime).

## What to Include

When reporting, please provide:

- **Description** of the vulnerability and its potential impact.
- **Steps to reproduce** or a proof of concept.
- **Affected version(s)** of ProtonShift.
- **Environment** details (distro, desktop environment, GPU).
- **Suggested fix**, if you have one.

## Response Timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 7 days |
| Fix or mitigation | Varies by severity |
| Public disclosure | After a fix is released |

## Scope

The following areas are in scope for security reports:

- **VDF / config writes** — unintended modification of Steam or Heroic config files.
- **Python backend** — command injection through launch options, env vars, or path arguments.
- **Electron IPC** — unauthorized access through the preload bridge.
- **File operations** — path traversal in prefix delete, save backup/restore, or open-path.
- **Environment variables** — injection via `environment.d` writes.
- **Protontricks execution** — unvalidated verb or argument passthrough.

## Out of Scope

- Vulnerabilities in upstream dependencies (report those to the respective project).
- Issues requiring physical access to an already-unlocked machine.
- Social engineering attacks.
- Bugs in Steam, Heroic, Lutris, MangoHud, or Gamescope themselves.

## Recognition

We're happy to credit security researchers in the release notes unless you prefer to remain anonymous. Let us know your preference when reporting.
