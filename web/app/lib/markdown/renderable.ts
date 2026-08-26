// Step 2 — the streaming-markdown problem, and the two answers to it.
//
// A markdown renderer is handed the WHOLE text on every token. While the
// model is still typing, that text can stop in the middle of a marker, and
// `**very` legitimately means two asterisks followed by a word.

/**
 * The hand-built answer: hide the unfinished part.
 *
 * An even number of pieces means an odd number of `**`, which means one of
 * them is still open — so drop everything after it and rejoin.
 *
 * Kept as the record of the version written before meeting the library.
 * Not in use: it hides text that streamdown can render straight away.
 */
export function handleMarkDown(text: string, streaming: boolean) {
  if (!streaming) return text;

  const parts = text.split("**");
  if (parts.length % 2 === 0) {
    parts.pop();
    text = parts.join("**");
  }

  if (text.endsWith("*") && !text.endsWith("**")) {
    text = text.slice(0, -1);
  }

  return text;
}

/**
 * The answer used with streamdown: trim a marker that has nothing after it.
 *
 * Streamdown closes an unfinished marker for you — `I am **very` is rendered
 * as `I am **very**` — so the text appears already styled instead of waiting.
 * The one case it cannot repair is a marker with no content yet: closing
 * `I am **` would give `****`, an empty bold. So it leaves it, and the
 * asterisks are on screen until the next character lands.
 *
 * This removes those frames. Everything else is left to streamdown.
 */
export function trimOpenMarker(text: string, streaming: boolean) {
  if (!streaming) return text;

  let end = text.length;
  while (end > 0 && text[end - 1] === "*") end--;
  return text.slice(0, end);
}
