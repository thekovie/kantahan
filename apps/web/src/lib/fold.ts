const APOSTROPHES = /['‘’`]/g;
const MARKS = /\p{M}/gu;
const SEPARATORS = /[^\p{L}\p{N}]+/gu;

/**
 * Matching form of a text: no case, no accents, apostrophes dropped (so "Ako'y" matches "akoy"),
 * other punctuation becomes a space. The catalog pipeline folds the same way.
 */
export function fold(text: string): string {
  return text
    .normalize("NFKD")
    .replace(MARKS, "")
    .toLowerCase()
    .replace(APOSTROPHES, "")
    .replaceAll("&", " and ")
    .replace(SEPARATORS, " ")
    .trim();
}
