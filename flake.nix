# This repository's flake -- the templates', not a generated project's (each template root's
# flake.nix is that): the tools its maintainers run, and the checks that need no network.
#
#   nix develop      the shell: the maintainers' tools -- cargo-generate, just, jq, shellcheck,
#                    shfmt, actionlint, dprint, cog, git-cliff, nixfmt, Python for render-check
#                    and sync; a project's own are its flake's (`just smoke` runs each there)
#   nix fmt          the formatter: nixfmt, shfmt (as .editorconfig says) and just's own, through
#                    treefmt; `nix fmt -- --ci` (`just nix`) formats, and fails if that changed a
#                    file
#   nix flake check  the format (the formatter's verdict), the shell (`just shell-check
#                    template-shell-check`: the root's and every template's) and the workflows
#                    (`just actionlint`), offline in the sandbox
#
# flake.lock is typst/flake.lock: one original, shared/root/flake.lock, copied to both by `just
# sync` (`just sync --check` holds them), so the tools here are at a typst project's versions, and
# the inputs are typst's -- package-check among them, which nothing here uses.
{
  description = "templates: the development shell and checks of cargo-generate templates";

  # typst's inputs (typst/flake.nix), as the one lock locks them (`just flake-sync`)
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    package-check = {
      url = "github:typst/package-check/v0.7.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, ... }:
    let
      inherit (nixpkgs) lib;
      # nixpkgs-unstable's platforms: it dropped x86_64-darwin in 26.11
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];

      perSystem =
        pkgs:
        let
          # `just --fmt` takes one justfile at a time; treefmt passes several
          justFmt = pkgs.writeShellApplication {
            name = "just-fmt";
            runtimeInputs = [ pkgs.just ];
            text = ''
              for justfile in "$@"; do
                just --fmt --unstable --justfile "$justfile"
              done
            '';
          };
          # `nix fmt`: each tool on its own files -- the shell scripts by extension, the hooks (the
          # root's, shared/root's and every template's) by their directory, as they have none; the
          # justfiles by name, the root's and every template's. python's and rust's flake.nix hold
          # Liquid, which no Nix parser reads: the generated project's formatter checks it,
          # rendered. The Typst code is typst's, with Liquid in it too: typstyle formats it in a
          # generated project, not here.
          formatter = pkgs.treefmt.withConfig {
            settings = {
              on-unmatched = "info";
              formatter = {
                nixfmt = {
                  command = "nixfmt";
                  includes = [ "*.nix" ];
                  excludes = [
                    "python/flake.nix"
                    "rust/flake.nix"
                  ];
                };
                shfmt = {
                  command = "shfmt";
                  options = [ "--write" ];
                  includes = [
                    "*.sh"
                    ".githooks/*"
                    "*/.githooks/*"
                  ];
                };
                just = {
                  command = "just-fmt";
                  includes = [
                    "justfile"
                    "*/justfile"
                  ];
                };
              };
            };
            runtimeInputs = [
              pkgs.nixfmt
              pkgs.shfmt
              justFmt
            ];
          };
          # a check on a writable copy, in a repository of its own: the recipes list git's files.
          # The sandbox has no /usr/bin/env, which the justfiles' script recipes name: their bash
          # is named by its path instead (to `just shell-check`, the same shell either way).
          onCopy =
            name: nativeBuildInputs: script:
            pkgs.runCommand name { inherit nativeBuildInputs; } ''
              cp -r ${./.} "$TMPDIR/repository"
              chmod -R u+w "$TMPDIR/repository"
              cd "$TMPDIR/repository"
              export HOME="$TMPDIR"
              substituteInPlace justfile */justfile \
                --replace-fail '#!/usr/bin/env bash' '#!${pkgs.bash}/bin/bash'
              git init --quiet
              git add --all
              ${script}
              touch $out
            '';
          shellTools = [
            pkgs.just
            pkgs.jq
            pkgs.gitMinimal
            pkgs.shellcheck
            pkgs.shfmt
          ];
        in
        {
          checks = {
            # the formatter's verdict on the whole tree: what `nix fmt` would change fails it
            format = formatter.check ./.;
            shell = onCopy "shell" shellTools "just shell-check template-shell-check";
            workflows = onCopy "workflows" (shellTools ++ [ pkgs.actionlint ]) "just actionlint";
          };

          devShells.default = pkgs.mkShell {
            packages = [
              pkgs.cargo-generate
              pkgs.just
              pkgs.jq
              pkgs.shellcheck
              pkgs.shfmt
              pkgs.actionlint
              pkgs.dprint
              pkgs.cocogitto
              pkgs.git-cliff
              pkgs.nixfmt
              # render-check's: it installs python-liquid, which nixpkgs lacks, into .venv; and
              # sync's and `just generate`'s
              pkgs.python3
            ];
          };

          inherit formatter;
        };

      bySystem = lib.genAttrs systems (system: perSystem nixpkgs.legacyPackages.${system});
      output = name: lib.mapAttrs (_: outputs: outputs.${name}) bySystem;
    in
    {
      checks = output "checks";
      devShells = output "devShells";
      formatter = output "formatter";
    };
}
