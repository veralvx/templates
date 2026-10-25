## Problem

[Describe the exact bug, limitation, or requirement this PR addresses.]

## Proposed Solution

[Describe the change and anything about the approach that is not obvious from the diff.]

## Verification

- [ ] Passes local CI (`just checks`).
- [ ] A change to a template passes `just smoke <template> <kind>` for each of its kinds: typst's
      `package` and `template`; python's `bin`, `lib` and `workspace`; rust's `bin`, `lib`, `both`
      and `workspace`.
- [ ] A shared file changed in its original under `shared/`, then `just sync` (AGENTS.md, Copies
      stay copies).
- [ ] Commits follow [Conventional Commits](https://www.conventionalcommits.org/), a template's
      scoped by its name.
