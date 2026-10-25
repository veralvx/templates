# {{project-name}}

{{description}}

## Requirements

Python {{python_min}} or later.

## Install
{% if project_kind == "lib" %}
```sh
uv add {{project-name}}
```
{% elsif project_kind == "workspace" %}
```sh
uv tool install {{project-name}}
```

The library alone:

```sh
uv add {{project-name}}-core
```
{% else %}
```sh
uv tool install {{project-name}}
```
{% endif %}
With Nix, `nix {% if project_kind == "lib" %}build{% else %}run{% endif %} github:{{github_username}}/{{project-name}}`.
{%- if project_kind != "lib" and container_image %}

As an OCI image, for Linux on amd64 and arm64:

```sh
docker run --rm ghcr.io/{{ github_username | downcase }}/{{project-name}} --version
```
{%- endif %}

## Usage
{% if project_kind == "lib" %}
```python
from {{crate_name}} import greeting

assert greeting("Ada") == "Hello, Ada!"
```
{% elsif project_kind == "workspace" %}
```sh
{{project-name}} Ada
```

The logic lives in `{{project-name}}-core`, usable on its own:

```python
from {{crate_name}}_core import greeting

assert greeting("Ada") == "Hello, Ada!"
```
{% else %}
```sh
{{project-name}} Ada
```

or, as a library:

```python
from {{crate_name}} import greeting

assert greeting("Ada") == "Hello, Ada!"
```
{% endif %}
{% if project_kind == "workspace" -%}
## Layout

- `pyproject.toml` -- the workspace: its tool groups and configuration
- `packages/{{project-name}}/` -- the command line: argument handling only; the main package
  (`[tool.{{project-name}}] main = true`), the flake's default, its image and the latest release
- `packages/{{project-name}}-core/` -- the library: everything worth testing
- `tests/` -- the workspace as a whole

Each member is its own distribution, with its own version, changelog and tag
(`<package>-v<version>`): `just release <package> <level>`. A new member is a folder
`packages/<name>/`, named as its distribution, with its pyproject.toml, README.md, `src/` and copies
of the licence files (its sdist holds its folder only); the root's ruff, basedpyright, pytest and
coverage settings name the members' folders and import names, so add it there too
(`tests/test_workspace.py` checks it). A requirement on another member needs `[tool.uv.sources]
<name> = { workspace = true }` too: without it, uv refuses to lock.

{% endif -%}
## Development

This repository uses [`just`](https://github.com/casey/just) to mirror CI locally. `just checks`
runs what the workflows run -- the lock, ruff, the shell, the workflows, the types, dead code, the
tests with their coverage gate, dprint, the commit messages, pip-audit, and last the flake's
formatter and checks:

```sh
just checks
```

See [CONTRIBUTING.md](https://github.com/{{github_username}}/{{project-name}}/blob/main/CONTRIBUTING.md)
for the tools those checks need, how a release is cut and, in a project just generated, its
[first steps](https://github.com/{{github_username}}/{{project-name}}/blob/main/CONTRIBUTING.md#first-steps); and
[AGENTS.md](https://github.com/{{github_username}}/{{project-name}}/blob/main/AGENTS.md) for the lint and
type policy and what to do when a rule fires.

## License
{% if license == "MIT OR Apache-2.0" %}
Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in
the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without
any additional terms or conditions.
{%- elsif license == "MIT" %}
Licensed under the MIT license ([LICENSE-MIT](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-MIT) or
<http://opensource.org/licenses/MIT>).
{%- else %}
Licensed under the Apache License, Version 2.0 ([LICENSE-APACHE](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-APACHE) or
<http://www.apache.org/licenses/LICENSE-2.0>).
{%- endif %}
