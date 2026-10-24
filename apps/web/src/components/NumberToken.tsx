import type { CSSProperties } from "react";

interface NumberTokenProps {
  /** The song number as text; leading zeros are part of it. */
  number: string;
  /** Larger variant for the read-out. */
  large?: boolean;
}

/**
 * The song number as heavy plain figures. Read aloud as separate digits, so "00589" is not heard as a
 * quantity. The visible text is hidden from assistive technology to avoid saying it twice.
 */
export function NumberToken({ number, large = false }: NumberTokenProps) {
  const digits = [...number];
  return (
    <span
      className={large ? "num num--large" : "num"}
      role="img"
      aria-label={`Song number ${digits.join(" ")}`}
      style={{ "--n": digits.length } as CSSProperties}
    >
      <span aria-hidden="true">{number}</span>
    </span>
  );
}
