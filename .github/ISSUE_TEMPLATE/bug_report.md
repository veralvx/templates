---
name: Bug Report
about: Report a generation that fails, or a generated project that misbehaves
title: "bug: "
labels: "bug"
assignees: ""
---

## Context

- **The template (typst, python or rust):**
- **cargo-generate version (`cargo generate --version`):**
- **This repository's commit, or release tag:**
- **The answers given** (the `cargo generate` command, with its `-d` values):

## Expected Behavior

[Describe what should have happened.]

## Actual Behavior

[Describe the failure. Include the error as printed: cargo-generate's, or the generated project's
`just checks` or CI's.]

## Reproduction

```sh
cargo generate --git https://github.com/veralvx/templates <template> ...
```
