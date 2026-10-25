# The Pythons .python-versions lists, oldest first, as nixpkgs' package sets: the one place the
# Nix files read them (the packages and the shell, the oldest; the tests and types, `checked`).
{ pkgs }:
let
  inherit (pkgs) lib;
  versions = lib.filter (v: v != "") (lib.splitString "\n" (lib.readFile ../.python-versions));
  # "3.13" -> pkgs.python313Packages
  packagesFor = version: pkgs."python${lib.replaceStrings [ "." ] [ "" ] version}Packages";
  # the ones nixpkgs builds, and so caches: the sets its release recurses into
  # (pkgs/top-level/release-lib.nix). Another's would build from source on every CI run, its
  # packages' test suites too -- CI's uv matrix tests it on PyPI's wheels instead. None listed: the
  # oldest, so the flake still tests one.
  cached = lib.filter (
    version:
    let
      set = packagesFor version;
    in
    set.recurseForDerivations or false || set.recurseForRelease or false
  ) versions;
in
{
  inherit versions packagesFor cached;
  oldest = packagesFor (lib.head versions);
  checked = if cached == [ ] then [ (lib.head versions) ] else cached;
}
