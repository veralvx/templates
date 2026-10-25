// The package's public API: what this file imports is what
// `#import "@preview/{{project-name}}:..."` exposes. Every other definition stays private to its
// module.
{%- if project_kind == "template" %}
#import "report.typ": report
{%- else %}
#import "greet.typ": greet
{%- endif %}
