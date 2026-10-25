// What `greet` accepts and refuses, asserted: compile-only, nothing rendered.
#import "/src/lib.typ": greet

// a string greets as its content does
#assert.eq(greet("Ada"), greet[Ada])

// anything else is refused, naming the parameter and what was given
#assert.eq(
  catch(() => greet(42)),
  "assertion failed: greet: `name` must be a string or content, not integer",
)
