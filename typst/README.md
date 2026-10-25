# {{project-name}}

{{description}}
{% if project_kind == "template" %}
## Usage

Start a project from it in the web app (*Start from template*, then search for
`{{project-name}}`), or on the command line:

```sh
typst init @preview/{{project-name}}:0.1.0
```

That makes a directory holding `main.typ`, which applies the template to the whole document with
a show rule:

```typ
#import "@preview/{{project-name}}:0.1.0": report

#show: report.with(
  title: [The Report's Title],
  authors: ("Author Name",),
  date: datetime.today(),
)

= Introduction
#lorem(40)
```

## Configuration

`report` takes, all optional:

| Parameter | Type                    | Default | What it sets                                     |
| --------- | ----------------------- | ------- | ------------------------------------------------ |
| `title`   | content, string or none | `none`  | the title block's heading, and the PDF's title   |
| `authors` | array of strings        | `()`    | the names under the title, and the PDF's authors |
| `date`    | datetime or none        | `none`  | the date under the authors, in English           |
| `paper`   | string                  | `"a4"`  | the paper size: one of Typst's, as `page` takes  |

The page has 2.5 cm margins and is numbered; headings are numbered; paragraphs are justified. The
paper size is `report`'s to set: a `#set page(...)` of your own would start a new page.
The fonts are Typst's own, so the document looks the same in the web app and on the command line.
{% else %}
## Usage

```typ
#import "@preview/{{project-name}}:0.1.0": greet

#greet[World]

#greet("Typst")
```

## Reference

### `greet(name) -> content`

The sentence `Hello, <name>!`.

- `name` (string or content): who to greet. Anything else is an error that names what was
  given.
{% endif %}
## Contributing

The source, issues and the development guide are at
<https://github.com/{{github_username}}/{{project-name}}>.

## License
{% if license == "MIT OR Apache-2.0" %}
Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.
{%- elsif license == "MIT" %}
Licensed under the MIT license ([LICENSE](LICENSE) or <http://opensource.org/licenses/MIT>).
{%- elsif license == "Apache-2.0" %}
Licensed under the Apache License, Version 2.0 ([LICENSE](LICENSE) or
<http://www.apache.org/licenses/LICENSE-2.0>).
{%- else %}
Licensed under the MIT No Attribution license ([LICENSE](LICENSE) or
<https://opensource.org/license/mit-0>){% if project_kind == "template" %}, the files in `template/` -- which
`typst init` copies into a new project -- included: what you make from them is yours to use and
share, no attribution needed{% endif %}.
{%- endif %}
{%- if project_kind == "template" and license != "MIT-0" %}

The files in `template/`, which `typst init` copies into a new project, are under the MIT No
Attribution license instead ([LICENSE-MIT-0](LICENSE-MIT-0) or
<https://opensource.org/license/mit-0>): what you make from them is yours to use and share, no
attribution needed.
{%- endif %}
{%- if license == "MIT OR Apache-2.0" %}

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in
the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without
any additional terms or conditions.
{%- endif %}
