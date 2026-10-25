/// Lays a report out: its title block, then the body, sections numbered. Apply it to the whole
/// document with a show rule:
///
/// ```typ
/// #show: report.with(title: [A report], authors: ("Jane Doe",))
/// ```
///
/// -> content
#let report(
  /// The report's title, also its PDF's.
  ///
  /// -> str | content | none
  title: none,
  /// Who wrote it, in order: the title block lists them, the PDF's metadata too.
  ///
  /// -> array
  authors: (),
  /// When it was written; shown under the authors when given.
  ///
  /// -> datetime | none
  date: none,
  /// The paper size, one of Typst's (`"a4"`, `"us-letter"`...): a page set rule of the user's own
  /// would start a new page, so the size is chosen here.
  ///
  /// -> str
  paper: "a4",
  /// The document.
  ///
  /// -> content
  body,
) = {
  assert(
    title == none or type(title) in (str, content),
    message: "report: `title` must be a string, content or none",
  )
  assert(
    type(authors) == array and authors.all(author => type(author) == str),
    message: "report: `authors` must be an array of strings",
  )
  assert(
    date == none or type(date) == datetime,
    message: "report: `date` must be a datetime or none",
  )
  assert(type(paper) == str, message: "report: `paper` must be a string")

  set document(title: title, author: authors)
  set page(paper: paper, margin: 2.5cm, numbering: "1")
  set par(justify: true)
  set heading(numbering: "1.")

  align(center, {
    if title != none {
      block(text(1.75em, weight: "bold", title))
    }
    if authors.len() > 0 {
      block(authors.join(", "))
    }
    if date != none {
      block(date.display("[month repr:long] [day padding:none], [year]"))
    }
  })
  v(1em)

  body
}
