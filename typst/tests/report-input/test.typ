// What `report` accepts and refuses, asserted: compile-only, nothing rendered.
#import "/src/lib.typ": report

#assert.eq(
  catch(() => report(title: 2026)[]),
  "assertion failed: report: `title` must be a string, content or none",
)

#assert.eq(
  catch(() => report(authors: "Jane Doe")[]),
  "assertion failed: report: `authors` must be an array of strings",
)

#assert.eq(
  catch(() => report(date: "2026-01-15")[]),
  "assertion failed: report: `date` must be a datetime or none",
)

#assert.eq(
  catch(() => report(paper: 210mm)[]),
  "assertion failed: report: `paper` must be a string",
)
