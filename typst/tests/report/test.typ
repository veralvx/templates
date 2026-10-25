// How a report's first page looks, compared with ref/: `just update report` rewrites the
// reference once a change to it is intended. The date is fixed, so the reference is too.
#import "/src/lib.typ": report

#show: report.with(
  title: [A Report],
  authors: ("Jane Doe", "John Roe"),
  date: datetime(year: 2026, month: 1, day: 15),
)

= Introduction
#lorem(40)

== Scope
#lorem(30)
