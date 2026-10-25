// cargo-generate's pre hook (cargo-generate.toml's [hooks]): the project name is the package's
// name on Typst Universe, refused here, before a file is written -- past here only the
// typst/packages review would say so -- unless it is:
//   - kebab-case: lowercase ASCII letters and digits in words joined by single hyphens, a letter
//     first, as a Typst identifier needs (typst/packages, docs/manifest.md; package-check's
//     `manifest/package/name/kebab-case`);
//   - free of "typst", which those rules call redundant.
// And two answers a regex cannot judge (cargo-generate's has no lookaround): the description free
// of "typst" too, which package-check warns of and so `just checks` fails on; the GitHub handle at
// most 39 characters, as Universe's bundler checks it. What a hook cannot judge -- that the name
// is not the obvious, canonical one for what it does -- is the review's. cargo-generate runs the
// hook from the template and does not copy it.
let name = variable::get("project-name");
let kebab = name.len() > 0;
let previous = '-';
for (c, i) in name.chars() {
    let lower = c >= 'a' && c <= 'z';
    let digit = c >= '0' && c <= '9';
    let hyphen = c == '-';
    if !(lower || (digit && i > 0) || (hyphen && previous != '-')) {
        kebab = false;
    }
    previous = c;
}
if !kebab || previous == '-' {
    abort(`package name "${name}": not kebab-case (a-z and 0-9, single hyphens, a letter first) -- choose another name`);
}
if name.contains("typst") {
    abort(`package name "${name}": Typst Universe's names leave out "typst" -- choose another name`);
}
let description = variable::get("description");
description.make_lower();
if description.contains("typst") {
    abort(`description: Typst Universe's descriptions leave out "Typst", which package-check warns of -- choose another description`);
}
let handle = variable::get("github_username");
if handle.len() > 39 {
    abort(`GitHub handle "${handle}": longer than GitHub's 39 characters -- choose another`);
}
