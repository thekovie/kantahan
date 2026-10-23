interface NumberTokenProps {
  /** The song number as text; leading zeros are part of it. */
  number: string;
  /** Larger variant for the read-out. */
  large?: boolean;
  /** Light the digits up one after another (once, for the read-out). */
  tick?: boolean;
}

/**
 * The song number as a seven-segment display: a dark tile, faint unlit segments behind, lit digits
 * in the model's colour (set by a `hue-*` class on an ancestor). Read aloud as separate digits.
 */
export function NumberToken({ number, large = false, tick = false }: NumberTokenProps) {
  const digits = [...number];
  const classes = ["led", large ? "led--large" : "", tick ? "led--tick" : ""].filter(Boolean).join(" ");
  return (
    <span
      className={classes}
      role="img"
      aria-label={`Song number ${digits.join(" ")}`}
      data-ghost={digits.map(() => "8").join("")}
      style={{ "--n": digits.length } as React.CSSProperties}
    >
      <span className="led__digits" aria-hidden="true">
        {digits.map((digit, i) => (
          <span key={i} className="led__digit" style={{ "--i": i } as React.CSSProperties}>
            {digit}
          </span>
        ))}
      </span>
    </span>
  );
}
