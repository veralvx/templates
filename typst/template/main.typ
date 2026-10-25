#import "@preview/{{project-name}}:0.1.0": report

#show: report.with(
  title: [The Report's Title],
  authors: ("Author Name",),
  date: datetime.today(),
)

= Introduction
#lorem(80)

= Method
#lorem(120)

== Data
#lorem(60)

= Results
#lorem(90)
