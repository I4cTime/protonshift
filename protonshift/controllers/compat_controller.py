"""QObject bridge for the per-game Proton version selector.

Same shape as LaunchOptionsController: ``appId``-driven threaded load, stale
results discarded, fail-closed save. Backed by ``core.compat_tool`` which
targets the *correct* file