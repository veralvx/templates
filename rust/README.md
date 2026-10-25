# {{project-name}}

{{description}}

## Requirements

- Rust {{msrv}} or later (pinned in `rust-toolchain.toml`), or Nix: `nix develop`
  provides that toolchain{% if project_kind != "lib" %}, and `nix build` the binary{% endif %}.

## Install
{% if project_kind == "lib" %}
```sh
cargo add {{project-name}}
```
{% else %}
```sh
cargo install {{project-name}}
```

Or, with [`cargo-binstall`](https://github.com/cargo-bins/cargo-binstall), to
fetch a prebuilt binary from the GitHub release `dist` builds, instead of
compiling:

```sh
cargo binstall {{project-name}}
```
{% if container_image %}
As an OCI image, for Linux on amd64 and arm64:

```sh
docker run --rm ghcr.io/{{ github_username | downcase }}/{{project-name}}
```
{% endif %}{% endif %}
## Build from source

```sh
git clone https://github.com/{{github_username}}/{{project-name}}.git
cd {{project-name}}
cargo build --release
```

## Usage
{% if project_kind == "lib" %}
```rust
use {{crate_name}}::saturating_total;

assert_eq!(saturating_total(2, 3), 5);
```
{% elsif project_kind == "workspace" %}
```sh
{{project-name}}
```

The logic lives in `crates/{{project-name}}-core`, which is usable on its own:

```rust
use {{crate_name}}_core::saturating_total;

assert_eq!(saturating_total(2, 3), 5);
```
{% elsif project_kind == "both" %}
```sh
{{project-name}}
```

The crate is a library too (`cargo add {{project-name}}`):

```rust
use {{crate_name}}::saturating_total;

assert_eq!(saturating_total(2, 3), 5);
```
{% else %}
```sh
{{project-name}}
```
{% endif %}
{% if project_kind == "workspace" -%}
## Layout

- `Cargo.toml` -- the workspace root: shared metadata, lint policy, profiles
- `crates/{{project-name}}/` -- the binary: argument handling only
- `crates/{{project-name}}-core/` -- the library: everything worth testing

The lint policy is declared once at the root under `[workspace.lints]`; each
member inherits it with `[lints] workspace = true`. Add a member by creating
`crates/<name>/`, listing it in the root `members`, and giving it that same
two-line `[lints]` table -- a member that omits it silently opts out of the
policy -- and copies of the licence files, since its `.crate` holds its own
directory only.

{% endif -%}
## Development

This repository uses [`just`](https://github.com/casey/just) to mirror CI
locally. `just checks` runs the twelve checks the workflows run, on the
toolchain `rust-toolchain.toml` pins (CI runs check, test, clippy, fmt and docs
on the latest stable, where a newer lint can still fire, and the pinned
toolchain in its MSRV and Nix jobs):

```sh
just checks
```

See [CONTRIBUTING.md](https://github.com/{{github_username}}/{{project-name}}/blob/main/CONTRIBUTING.md)
for the toolchain those checks need, how a release is cut and, in a project
just generated, its [first steps](https://github.com/{{github_username}}/{{project-name}}/blob/main/CONTRIBUTING.md#first-steps);
and [AGENTS.md](https://github.com/{{github_username}}/{{project-name}}/blob/main/AGENTS.md) for the lint
policy and what to do when a lint fires.

## License
{% if license == "MIT OR Apache-2.0" %}
Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-MIT) or
  <http://opensource.org/licenses/MIT>)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.
{%- elsif license == "MIT" %}
Licensed under the MIT license ([LICENSE-MIT](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-MIT) or
<http://opensource.org/licenses/MIT>).
{%- else %}
Licensed under the Apache License, Version 2.0 ([LICENSE-APACHE](https://github.com/{{github_username}}/{{project-name}}/blob/main/LICENSE-APACHE)
or <http://www.apache.org/licenses/LICENSE-2.0>).
{%- endif %}
