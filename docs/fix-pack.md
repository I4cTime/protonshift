# Fix pack format (version 2)

The fix pack is the knowledge behind Diagnose: a list of rules, each of which
recognises one situation (a line in the Proton log, a setting, a known game)
and says what it means and what to change. This document is the contract for
that file. `protonshift/core/fix_pack.py` loads and validates it, and
`tests/test_fix_pack.py` fails the build when the bundled pack breaks any rule
written here. Change this document first, then the code.

The bundled pack is `protonshift/core/data/fix_pack.json`. Fixes a user adds
for themselves stay in `~/.config/protonshift/fixes/<appid>.json` in the
version 1 shape (see "User fixes" below).

## Why the format is strict

Steam hands a game's launch options to a shell. A rule that could write any
text into them would be a way to run any command the next time the game
starts. So a rule cannot contain free text that reaches the launch options:
it can only name an environment variable, a value from a narrow character
set, a single game argument, or a wrapper to remove. Everything a rule would
change is shown to the user before it is applied, and a snapshot is saved so
it can be undone.

The same rules apply to the bundled pack as to any pack loaded later from
elsewhere. Nothing here is relaxed because the file ships with the app.

## File shape

```json
{
  "format": "protonshift-fix-pack",
  "version": 2,
  "revision": "2026.11.1",
  "rules": [ { "...": "one rule, see below" } ]
}
```

- `format` must be exactly `protonshift-fix-pack`.
- `version` is the schema version, an integer. A pack with a higher version
  than the app understands is rejected whole.
- `revision` names this edition of the data: `YYYY.MM.N`.
- `rules` is a list. A rule that fails validation is dropped and reported;
  the other rules still load. (The test suite is stricter than the loader:
  for the bundled pack, any invalid rule fails the build.)

## A rule

```json
{
  "id": "wrapper-gamemoderun-missing",
  "title": "GameMode is in the launch options but is not installed",
  "cause": "Steam runs the game through gamemoderun, which was not found, so the game never starts.",
  "severity": "blocking",
  "match": {
    "app_ids": ["1091500"],
    "log": ["wine: could not load kernel32\\.dll"],
    "when": { "gpu_vendor": ["nvidia"], "session": ["wayland"] }
  },
  "actions": [
    { "type": "env", "key": "PROTON_ENABLE_NVAPI", "value": "1" }
  ],
  "source": "https://github.com/ValveSoftware/Proton/issues/0000",
  "verified": "2026-11-16"
}
```

| field | required | meaning |
|---|---|---|
| `id` | yes | Unique in the pack. Lowercase letters, digits and hyphens, 3 to 64 characters. |
| `title` | yes | What is wrong, in plain words, at most 100 characters. |
| `cause` | yes | One or two sentences a player can follow, at most 400 characters. |
| `severity` | yes | `blocking` (the game will not start), `likely` (probably the reason for the trouble), or `advice` (a known tweak; nothing is wrong). |
| `match` | yes | When the rule applies. See "Matching". |
| `actions` | yes | What to change. May be empty for a rule that only explains. See "Actions". |
| `source` | yes | An `https://` URL where the situation and the remedy can be checked: upstream source code, a public issue, or project documentation. |
| `verified` | yes | The date (`YYYY-MM-DD`) someone last checked the rule against its source. |

Titles and causes are plain text. They are shown as text, never as markup,
and may not be blank or contain line breaks or other control characters; the
same goes for the text of a `manual` action.

The loader is strict throughout. A key it does not know (in the pack, a
rule, `match`, `when` or an action) rejects that rule, so a typo cannot
silently produce a rule with defaults. A value of the wrong type is rejected,
never converted. An empty list is rejected. An id may not start with `user-`,
which is kept for the user's own fixes. A file with the same key twice in one
object is rejected whole.

## Matching

`match` holds up to four parts. Every part that is present must hold.
At least one of `app_ids` and `log`, or a `when` that uses `launch_has` or
`env_set`, must be present: a rule that matches every game on every machine
is not a rule.

- `app_ids`: a list of Steam App IDs (decimal digits only). The rule applies
  to those games. Absent means any game.
- `log`: a list of regular expressions (Python `re` syntax). The rule matches
  when any one of them is found in any single line of the log tail. Each
  expression must compile, must be at most 300 characters, and must contain
  at least 8 literal characters in a row, so that it is anchored on real text
  and not on a pattern that fits half the log. An expression must not repeat
  a group that itself contains a repeat (for example `(a+)+`), and may hold
  at most two open-ended repeats (`*`, `+`, `{n,}`), because such patterns
  can take a very long time on a long line. An optional group (`?`) does not
  count as repeating what is inside it. Inline flags, back-references and
  conditionals are not allowed. Matching is case sensitive, and only the
  first 2000 characters of a line are looked at.

  What counts toward the 8 literal characters: plain and escaped characters
  (`\.`), also through a group that is not repeated. A character class, `.`,
  an anchor, a repeat that may match zero times, and a lookaround end the
  run. An alternation counts as its shortest branch.
  With no log on disk, a rule that has a `log` part does not match.
- `log_also`: a list of regular expressions under the same limits. Every one
  of them must also be found somewhere in the log tail, each in any line.
  It is only allowed together with `log`. Use it for a line that healthy
  games print too and that means trouble only next to another line: Wine
  reports a missing library for helper processes of games that run fine, so
  the missing-library rule also requires the line that says the game's own
  start failed. The line quoted to the user as evidence is the one `log`
  matched.
- `when`: conditions on the machine and the game's settings. All listed
  conditions must hold.

| condition | value | holds when |
|---|---|---|
| `gpu_vendor` | list of `nvidia`, `amd`, `intel` | any GPU of a listed vendor is present |
| `session` | list of `wayland`, `x11` | the desktop session is of a listed type |
| `proton_family` | list of `valve`, `ge`, `cachyos`, `other` | the game's Proton build belongs to a listed family |
| `proton_major_min` | integer, 0 or more | the build's major version is at least this |
| `proton_major_max` | integer, not below the minimum | the build's major version is at most this |
| `launch_has` | list of words (same characters as `remove_word`) | every listed word is in the launch options before `%command%`, as a command name (`gamemoderun`) |
| `env_set` | list of variable names | every listed variable is set in the launch options |
| `env_unset` | list of variable names | none of the listed variables is set in the launch options |

A fact the app could not find out never satisfies a condition. A game on
Steam's default Proton has no known family or version, so a rule with
`proton_major_max` does not match it. Diagnose prefers a missed finding to a
false one.

A rule with `app_ids` and no `log` is a known tweak for that game. It must
have severity `advice`.

## Actions

Each action is one small, reversible change to the game's settings, or an
instruction for the user. A rule may list several; they are applied together
and undone together.

| `type` | fields | effect |
|---|---|---|
| `env` | `key`, `value` | Set `KEY=value` in the launch options, before `%command%`. Replaces an existing assignment of the same key. |
| `unset_env` | `key` | Remove the assignment of `KEY` from the launch options. |
| `game_arg` | `value` | Add one argument for the game, after `%command%`. |
| `remove_word` | `value` | Remove a wrapper command (for example `gamemoderun`) from before `%command%`. |
| `default_proton` | none | Stop forcing a Proton build for this game; Steam picks one. |
| `manual` | `text` | Nothing is changed. The text tells the user what to do (install a package, verify game files). At most 300 characters. |

Limits, enforced by the loader:

- `key` matches `^[A-Za-z_][A-Za-z0-9_]*$`.
- `value` for `env` matches `^[A-Za-z0-9_.,:=/+@%-]{0,200}$`. No spaces, no
  quotes, no shell characters.
- `value` for `game_arg` matches `^[-+][A-Za-z0-9_.=:-]{1,60}$` (one switch,
  such as `-vulkan` or `+fps_max=0`).
- `value` for `remove_word` matches `^[A-Za-z0-9_.-]{1,40}$`.
- An `env` value may not contain `%command%`: Steam replaces it wherever it
  appears, also inside an assignment.
- A rule has at most 6 actions. No action is listed twice, and no two
  actions of one rule touch the same variable.
- These variables may never be set or unset by a rule, because they decide
  what code a process loads or runs: `LD_PRELOAD`, `LD_LIBRARY_PATH`,
  `LD_AUDIT`, `PATH`, `PYTHONPATH`, `STEAM_COMPAT_LAUNCHER_SERVICE`,
  `WINEDLLPATH`, and any name starting with `STEAM_COMPAT_`.

A game argument can only be placed after `%command%`; there is no action
that puts text in front of it other than `env`. This is by construction, so a
rule cannot repeat the version 1 mistake of writing `-vulkan %command%`.

## User fixes

A file under `~/.config/protonshift/fixes/<appid>.json` is a list of
version 1 entries:

```json
[ { "title": "...", "description": "...", "type": "env", "key": "DXVK_HUD", "value": "fps" } ]
```

`type` is `env` (uses `key` and `value`) or `launch_arg` (uses `value`).
Each entry is shown in Diagnose as an `advice` finding marked as the user's
own. A user entry is the user's own text on the user's own machine, so its
value is not held to the character limits above; the key still must match
the key pattern, and the change is still shown before it is applied. A
`launch_arg` value that contains `%command%` is merged the way the app merges
any snippet; one without it is treated as game arguments.

## Adding a rule

1. Find the source: the line in upstream code that prints the message, a
   public issue where the fix was confirmed, or a documentation page.
2. Write the narrowest match that fits. For a log rule, copy the fixed part
   of the message; do not match on `err:` or `fixme:` alone.
3. Check that the line does not also appear in the log of a game that runs
   fine. Many `fixme:` and some `err:` lines do.
4. Add the rule to `fix_pack.json`, set `verified` to today, bump `revision`.
5. Run `pytest tests/test_fix_pack.py`.
