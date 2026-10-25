// How a greeting looks, compared with ref/: `just update greet` rewrites the reference once a
// change to it is intended.
#import "/src/lib.typ": greet

#set page(width: auto, height: auto, margin: 1em)

#greet[World]

#greet("Typst")
