/// Greets someone by name.
///
/// ```example
/// #greet[World]
/// ```
///
/// -> content
#let greet(
  /// Who to greet.
  ///
  /// -> str | content
  name,
) = {
  assert(
    type(name) in (str, content),
    message: "greet: `name` must be a string or content, not "
      + str(type(name)),
  )
  [Hello, #name!]
}
