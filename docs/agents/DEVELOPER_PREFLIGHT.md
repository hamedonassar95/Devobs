# Developer environment preflight (read-only)

`scripts/developer_preflight.py` is a local, advisory preflight for Devobs
contributors. It answers one narrow question: **can the documented verification
commands be attempted in this checkout?** It does not answer whether those
commands pass.

The script performs no writes, installs, container starts, cloud calls,
network requests, or agent dispatch. It does not read environment variable
values or secrets. It never executes a documented verification command. The
only child processes are fixed, allowlisted version probes (`python --version`,
`node --version`, `git --version`, `docker --version`, `terraform version`, and
`npm --version`); Bandit's version comes from local distribution metadata. The
parsed version is retained, but raw probe output is discarded. Unexpected
output is reported as `UNVERIFIED`, never printed.

## Usage

From the repository root:

```sh
python scripts/developer_preflight.py --help
python scripts/developer_preflight.py --repo .
```

On Windows PowerShell the same commands apply; `py -3` may be substituted for
`python` when that is the operator's documented interpreter launcher. The
script supports Windows and Linux by resolving executables through Python's
standard `shutil.which` behavior and by never constructing platform-specific
shell strings.

Verification of the preflight itself uses the documented commands:

```sh
python -m unittest discover -s tests -p "test_developer_preflight.py" -v
python scripts/developer_preflight.py --help
python -m compileall -q scripts
git diff --check
```

Related repository checks represented in the report include
`python -m unittest discover -s tests -p "test_*.py" -v`,
`npm test`, `npm run lint`, `npm run build`,
`python -m bandit -r scripts tools -x scripts/check_site.py`,
`terraform -chdir=infra/terraform fmt -check`, and
`terraform -chdir=infra/terraform validate`. Their exact documentation sources
are recorded in each JSON entry.

## JSON contract

The tool prints one JSON object and no other stdout. It exits `0` when no
prerequisite is blocked, `1` when at least one prerequisite is blocked, and
`2` on an internal failure. Top-level fields are:

- `schema_version`: currently `1`.
- `mode`: always `READ_ONLY`.
- `repository_root` and `platform`: the inspected local checkout and platform.
- `overall_status`: `BLOCKED` if any tool or command entry is blocked;
  otherwise `UNVERIFIED`. It is never `VERIFIED` because no documented command
  is executed.
- `commands_executed`: always `false`.
- `environment_values_read`: always `false`.
- `tools` and `documented_commands`: the detailed evidence entries.
- `summary`: counts of `verified`, `blocked`, and `unverified` entries.
- `errors`: generic, non-sensitive failure categories only.

Each tool entry contains `id`, `label`, `status`, `version`, `probe`, and
`reason`. Each documented-command entry contains `id`, `command`, `source`,
`status`, `reason`, `required_tools`, `missing_tools`, `unverified_tools`,
`missing_paths`, and `executed: false`.

### Evidence meanings

- `VERIFIED`: the tool was found and its allowlisted version probe returned a
  recognized version, or the required local path exists. This is evidence about
  availability only.
- `BLOCKED`: a required executable, distribution, or path is missing, or a
  version probe failed. Treat dependent documented commands as not runnable.
- `UNVERIFIED`: prerequisites are present but the command was not run, or a
  probe returned an unexpected result. Missing evidence never becomes a pass.

Fail-closed behavior is deliberate: a missing executable, a non-zero probe, a
timeout, a malformed version string, or a missing path cannot silently become
`VERIFIED`. Raw probe text, exception text, environment values, and secret-like
data are excluded from the report.

## Checked tool families

| Tool | Probe | Why it is checked |
| --- | --- | --- |
| Python | `python --version` (fallback `python3 --version`) | unittest, compileall, Bandit invocation |
| Node.js | `node --version` | console test runtime |
| Git | `git --version` | `git diff --check` |
| Docker | `docker --version` | documented local container workflows |
| Terraform | `terraform version` | documented `fmt -check` and `validate` |
| npm | `npm --version` | console `test`, `lint`, and `build` |
| Bandit | local distribution metadata | documented Python security scan |

The version flags and APIs above follow the official documentation:
[Python `--version`](https://docs.python.org/3/using/cmdline.html#cmdoption-version),
[Node.js `--version`](https://nodejs.org/api/cli.html#node---version),
[Git `--version`](https://git-scm.com/docs/git#Documentation/git.txt---version),
[Docker `--version`](https://docs.docker.com/reference/cli/docker/version/),
[Terraform `version`](https://developer.hashicorp.com/terraform/cli/commands/version),
[npm `--version`](https://docs.npmjs.com/cli/v7/commands/npm-version),
[Bandit version via `importlib.metadata.version`](https://docs.python.org/3/library/importlib.metadata.html#importlib.metadata.version),
[`shutil.which`](https://docs.python.org/3/library/shutil.html#shutil.which),
and [`subprocess.run`](https://docs.python.org/3/library/subprocess.html#subprocess.run).

## Boundaries

A preflight `VERIFIED` tool is not proof that CI passed, that dependencies are
installed, that Terraform is initialized, that a Docker daemon is available,
or that any command succeeded. A human must still run the relevant commands
and record fresh output. This tool does not change P01, AI-9, Codex runtime
acceptance, branch protection, or merge/deploy authority.
