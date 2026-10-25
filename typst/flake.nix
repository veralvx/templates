# The package's flake: every tool whose verdict depends on its version -- typst, tytanic,
# typstyle, tinymist, just, shellcheck, shfmt and actionlint from nixpkgs, typst-package-check
# from its own repository, at its tag -- the others `just checks` and `just release` run, and the
# checks that need no network. Their versions are the ones flake.lock locks, which is why it is
# committed: CI's are the same (`packages.tools`), and `nix flake update` (or Dependabot's) moves
# them all -- if Typst moved, `just update` the references its rendering changed.
#
#   nix develop      the shell: the tools, typst-package-check, dprint, cog, git-cliff, nixfmt
#   nix build .#tools
#                    the tools CI runs (.github/install-tools.sh), typst-package-check aside:
#                    nixpkgs builds none of it, so CI runs its image, at the input's tag
#   nix fmt          the formatter: nixfmt, shfmt (as .editorconfig says), typstyle and just's
#                    own, through treefmt; `nix fmt -- --ci` (`just nix`) formats, and fails if
#                    that changed a file
#   nix flake check  the format (the formatter's verdict), the lints (`just lint`: tinymist), the
#                    shell (`just shell-check`: shellcheck and shfmt, the justfile's script recipes
#                    too), the workflows (actionlint), the tests (tytanic) and typst-package-check
#                    built, offline in the sandbox
{
  description = "A Typst package's development shell and checks";

  inputs = {
    # the unstable channel: Typst releases reach it within days; a release channel's lags behind
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    package-check = {
      url = "github:typst/package-check/v0.7.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, package-check, ... }:
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
          typst-package-check = package-check.packages.${pkgs.stdenv.hostPlatform.system}.default;
          # what the tests read: the package and its tests, so an edit elsewhere reruns nothing
          testSource = lib.fileset.toSource {
            root = ./.;
            fileset = lib.fileset.unions (
              map lib.fileset.maybeMissing [
                ./typst.toml
                ./src
                ./template
                ./tests
              ]
            );
          };
          # CI's (checks.yml's and publish.yml's, through .github/install-tools.sh), the dev shell's
          # too: jq reads typst.toml with Typst (`just manifest`), actionlint runs shellcheck on each
          # `run:` script
          tools = [
            pkgs.typst
            pkgs.tytanic
            pkgs.typstyle
            pkgs.tinymist
            pkgs.just
            pkgs.jq
            pkgs.shellcheck
            pkgs.shfmt
            pkgs.actionlint
          ];
          # `nix fmt`: each tool on its own files -- the shell scripts by extension, the hooks by
          # their directory, as they have none; the justfile by name, as `just --fmt` takes one
          formatter = pkgs.treefmt.withConfig {
            settings = {
              on-unmatched = "info";
              formatter = {
                nixfmt = {
                  command = "nixfmt";
                  includes = [ "*.nix" ];
                };
                shfmt = {
                  command = "shfmt";
                  options = [ "--write" ];
                  includes = [
                    "*.sh"
                    ".githooks/*"
                  ];
                };
                typstyle = {
                  command = "typstyle";
                  options = [ "--inplace" ];
                  includes = [ "*.typ" ];
                };
                just = {
                  command = "just";
                  options = [
                    "--fmt"
                    "--unstable"
                    "--justfile"
                  ];
                  includes = [ "justfile" ];
                };
              };
            };
            runtimeInputs = [
              pkgs.nixfmt
              pkgs.shfmt
              pkgs.typstyle
              pkgs.just
            ];
          };
        in
        {
          packages.tools = pkgs.buildEnv {
            name = "tools";
            paths = tools;
          };

          checks = {
            # built, not just evaluated: nixpkgs carries no build of it, so a `nix flake update`
            # its build no longer accepts fails here, not at a contributor's `nix develop`
            inherit typst-package-check;

            # the formatter's verdict on the whole tree: what `nix fmt` would change fails it
            format = formatter.check ./.;

            # `just lint` on a copy: its script recipe's bash named by its path, as below
            lint =
              pkgs.runCommand "lint"
                {
                  nativeBuildInputs = [
                    pkgs.just
                    pkgs.jq
                    pkgs.typst
                    pkgs.tinymist
                  ];
                }
                ''
                  cp -r ${./.} "$TMPDIR/package"
                  chmod -R u+w "$TMPDIR/package"
                  cd "$TMPDIR/package"
                  export HOME="$TMPDIR"
                  substituteInPlace justfile \
                    --replace-fail '#!/usr/bin/env bash' '#!${pkgs.bash}/bin/bash'
                  just lint
                  touch $out
                '';

            # `just shell-check` on a copy, in a repository of its own: it lists the scripts git
            # does not ignore. The sandbox has no /usr/bin/env, which the script recipes name: their
            # bash is named by its path instead (to `just shell-check`, the same shell either way).
            shell =
              pkgs.runCommand "shell"
                {
                  nativeBuildInputs = [
                    pkgs.just
                    pkgs.jq
                    pkgs.gitMinimal
                    pkgs.shellcheck
                    pkgs.shfmt
                  ];
                }
                ''
                  cp -r ${./.} "$TMPDIR/package"
                  chmod -R u+w "$TMPDIR/package"
                  cd "$TMPDIR/package"
                  export HOME="$TMPDIR"
                  substituteInPlace justfile \
                    --replace-fail '#!/usr/bin/env bash' '#!${pkgs.bash}/bin/bash'
                  git init --quiet
                  git add --all
                  just shell-check
                  touch $out
                '';

            # actionlint on a copy, in a repository of its own, as `just actionlint` runs it: with
            # no file named, actionlint finds the workflows, and .github/actionlint.yaml if there is
            # one, from the repository's root
            workflows =
              pkgs.runCommand "workflows"
                {
                  nativeBuildInputs = [
                    pkgs.actionlint
                    pkgs.shellcheck
                    pkgs.gitMinimal
                  ];
                }
                ''
                  cp -r ${./.} "$TMPDIR/package"
                  chmod -R u+w "$TMPDIR/package"
                  cd "$TMPDIR/package"
                  export HOME="$TMPDIR"
                  git init --quiet
                  actionlint
                  touch $out
                '';

            # from a writable copy: tytanic writes each test's output beside it
            tests = pkgs.runCommand "tests" { nativeBuildInputs = [ pkgs.tytanic ]; } ''
              cp -r ${testSource} "$TMPDIR/package"
              chmod -R u+w "$TMPDIR/package"
              cd "$TMPDIR/package"
              export HOME="$TMPDIR"
              tt run --no-fail-fast --jobs "$NIX_BUILD_CORES"
              touch $out
            '';
          };

          devShells.default = pkgs.mkShell {
            packages = tools ++ [
              typst-package-check
              pkgs.dprint
              pkgs.cocogitto
              pkgs.git-cliff
              pkgs.nixfmt
            ];
          };

          inherit formatter;
        };

      bySystem = lib.genAttrs systems (system: perSystem nixpkgs.legacyPackages.${system});
      output = name: lib.mapAttrs (_: outputs: outputs.${name}) bySystem;
    in
    {
      packages = output "packages";
      checks = output "checks";
      devShells = output "devShells";
      formatter = output "formatter";
    };
}
