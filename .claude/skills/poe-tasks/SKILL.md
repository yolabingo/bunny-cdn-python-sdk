---
name: poe-tasks
description: Run, add, or change poethepoet (poe) tasks in the bunny-cdn-sdk repo. Use whenever you are about to run tests, lint, type-check, build, version-bump, release, or fetch API specs here (check for a poe task before calling pytest/ruff/ty/uv build directly), and whenever editing [tool.poe.tasks] in pyproject.toml or the task list in docs/BUILD.md, even if the user just says "add a command for X" or "make a script runnable".
---

# Poe tasks in bunny-cdn-sdk

This repo runs every dev workflow through [poethepoet](https://poethepoet.natn.io). Tasks live in `[tool.poe.tasks]` in `pyproject.toml` and always run as `uv run poe <task>`; per CLAUDE.md, never invoke tools such as pytest or ruff bare.

This skill covers only what is specific to this repo. For poe itself (task types, options, args, packages), read the **upstream poethepoet skill**, which the poe maintainers keep in step with each release. It is fetched fresh each time rather than copied in, so it is never stale.

## Step 1: Load the latest upstream guidance

```bash
bash .claude/skills/poe-tasks/scripts/fetch_upstream.sh
```

This sparse-clones (or updates) `nat-n/poethepoet` at the latest `main` and prints the local path, the upstream skill version, the installed poe version, and every reference file now present. Then:

1. **Read the upstream `SKILL.md`** from the printed path. It is short and holds the rules that matter most (the silent-failure rules for `expr`/`switch`, the `_` private prefix, "compose, don't recurse").
2. **Read the reference files that fit the task.** List them from the script output rather than assuming names, because upstream adds and renames them. As of poe 0.49.0 they were:
   - `references/creating-tasks.md`: read before creating or restructuring any task
   - `references/task-types.md`: cmd / script / shell / sequence / parallel / ref / expr / switch
   - `references/task-options.md`: help, env, deps, uses, cwd, executor, …
   - `references/args-reference.md`: named and positional CLI args
   - `references/task-packages.md`: reusable task packages
3. **Compare versions.** If upstream is newer than the installed poe, the docs may describe features this repo can't use yet. Check before relying on one, and offer to upgrade with `uv add --dev 'poethepoet>=X.Y'` (`[tool.uv] exclude-newer` holds back releases under 3 days old). If the installed poe is newer, the upstream `main` docs still apply.

If the fetch fails (offline, GitHub down), say so and fall back to https://poethepoet.natn.io or the installed source (`uv run python -c "import poethepoet, os; print(os.path.dirname(poethepoet.__file__))"`). Don't guess at poe behaviour; a quick `uv run poe -d <task>` dry run settles most questions.

Just running an existing task needs no fetch: `uv run poe` lists them, and `uv run poe <task>` runs one.

## Step 2: Follow this repo's conventions

These take precedence over generic upstream advice where they conflict.

- **Run through uv:** `uv run poe <task>`. Inside a task, `cmd` entries may call tools bare (`ruff check …`) because poe's uv executor already runs them in the project environment.
- **Grouping comments are the house style.** `pyproject.toml` groups tasks under `# --- setup ---`, `# --- test ---`, `# --- build ---` and similar headers. Upstream says not to add `#` comments to task config; follow that for explaining individual tasks (that belongs in `help`), but put new tasks under the right section header or add a new one.
- **Every task needs `help`.** Keep it to one line, aligned with its neighbours.
- **Keep docs/BUILD.md in sync.** Its "Available poe Tasks" section lists every task with a one-line comment, in the same groups. Add, rename or remove entries in the same change, or the docs drift (this has needed a fix-up commit before).
- **Scripts go in `tools/`.** Maintainer scripts (such as `tools/fetch_api_specs.py`) run as `cmd = "python tools/<script>.py"`. Ruff ignores for print and similar live under `"tools/**"` in `[tool.ruff.lint.per-file-ignores]`.
- **Leave the release task alone.** `release` tags and pushes, which triggers a PyPI publish. Don't change or run it unless the user explicitly asks.
- **Dependencies:** add with `uv add --dev …`, never by editing `[dependency-groups]` by hand. After any dependency or `uv.lock` change, run `uv run poe test-audit` (`uv audit`), which is also a prek hook. If it reports a vulnerability, upgrade the package (`uv lock --upgrade-package <pkg>`). Ignore a finding with `--ignore <ID>` in the task and the hook only when the user agrees, and record why.

## Step 3: Verify

```bash
uv run poe --help <task>   # parses, and the help text reads well
uv run poe -d <task>       # dry run: shows the exact command
uv run poe <task>          # actually run it if it's safe (not release/publish)
```

Before finishing, delete any throwaway tasks you added while experimenting.
