import { CheckCircle2, TriangleAlert } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "wouter";
import {
  type ContactField,
  type ContactInput,
  type ContactKind,
  type ContactResult,
  MESSAGE_MAX,
  checkContact,
  sendContact,
} from "../lib/contact";

const KINDS: readonly { value: ContactKind; label: string }[] = [
  { value: "removal", label: "Remove an entry" },
  { value: "correction", label: "Correct a number, title or artist" },
  { value: "other", label: "Something else" },
];
const EMPTY: ContactInput = { type: "", message: "", email: "", name: "", reference: "", website: "" };
const FIELD_ORDER: readonly ContactField[] = ["type", "reference", "message", "name", "email"];

interface ContactFormProps {
  /** Replace the network call (tests). */
  send?: (input: ContactInput) => Promise<ContactResult>;
}

const WORRY: Record<"slow-down" | "offline" | "unavailable", (minutes: number) => string> = {
  "slow-down": (minutes) => `Too many messages came from your network. Try again in about ${minutes} minute${minutes === 1 ? "" : "s"}.`,
  offline: () => "No connection. Your message is still here; send it when you are back online.",
  unavailable: () =>
    "The message could not be sent right now. Try again later, or open an issue on GitHub (it is public, so leave out personal details).",
};

/** Private contact form for rights and correction requests. Nothing is stored by the app. */
export function ContactForm({ send = sendContact }: ContactFormProps) {
  const [input, setInput] = useState<ContactInput>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<ContactField, string>>>({});
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const done = useRef<HTMLHeadingElement>(null);
  const refs = useRef<Partial<Record<ContactField, HTMLElement | null>>>({});

  useEffect(() => {
    if (sent) done.current?.focus();
  }, [sent]);

  const set = <K extends keyof ContactInput>(key: K, value: ContactInput[K]) => {
    setInput((current) => ({ ...current, [key]: value }));
    if (key in errors) setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const focusFirst = (found: Partial<Record<ContactField, string>>) => {
    const first = FIELD_ORDER.find((field) => found[field]);
    if (first) refs.current[first]?.focus();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (sending) return;
    setProblem(null);
    const found = checkContact(input);
    if (Object.keys(found).length > 0) {
      setErrors(found);
      focusFirst(found);
      return;
    }
    setSending(true);
    const result = await send(input);
    setSending(false);
    if (result.status === "sent") {
      setInput(EMPTY);
      setErrors({});
      setSent(true);
    } else if (result.status === "invalid") {
      setErrors(result.fields);
      focusFirst(result.fields);
    } else {
      setProblem(WORRY[result.status](result.status === "slow-down" ? result.minutes : 0));
    }
  };

  if (sent) {
    return (
      <section className="notice-panel" aria-live="polite">
        <CheckCircle2 size={32} aria-hidden="true" />
        <h3 ref={done} tabIndex={-1}>
          Message sent
        </h3>
        <p>Thank you. We read every request. If you left an e-mail address, the reply goes there.</p>
        <button type="button" className="btn btn--quiet" onClick={() => setSent(false)}>
          Send another message
        </button>
      </section>
    );
  }

  const error = (field: ContactField) => errors[field];
  const describe = (field: ContactField, hint?: string) =>
    [error(field) ? `${field}-error` : null, hint ?? null].filter(Boolean).join(" ") || undefined;

  return (
    <form className="form" onSubmit={submit} noValidate aria-label="Contact form">
      {problem && (
        <p className="notice-error" role="alert">
          <TriangleAlert size={20} aria-hidden="true" />
          {problem}
        </p>
      )}

      <fieldset className="form__group" aria-describedby={describe("type")} aria-invalid={error("type") ? true : undefined}>
        <legend>What is this about?</legend>
        <div className="choices">
          {KINDS.map((kind, index) => (
            <label key={kind.value} className="choice">
              <input
                ref={index === 0 ? (node) => void (refs.current.type = node) : undefined}
                type="radio"
                name="type"
                value={kind.value}
                checked={input.type === kind.value}
                onChange={() => set("type", kind.value)}
              />
              <span>{kind.label}</span>
            </label>
          ))}
        </div>
        {error("type") && (
          <p className="field__error" id="type-error">
            {error("type")}
          </p>
        )}
      </fieldset>

      <Field label="Which machine and song? (optional)" hint="For example: Reyna, 00589" error={error("reference")} id="reference">
        <input
          ref={(node) => void (refs.current.reference = node)}
          id="reference"
          className="field__input"
          value={input.reference}
          maxLength={200}
          autoComplete="off"
          aria-invalid={error("reference") ? true : undefined}
          aria-describedby={describe("reference", "reference-hint")}
          onChange={(event) => set("reference", event.target.value)}
        />
      </Field>

      <Field
        label="Message"
        meta={`${input.message.trim().length.toLocaleString("en-PH")} of ${MESSAGE_MAX.toLocaleString("en-PH")} characters`}
        error={error("message")}
        id="message"
        required
      >
        <textarea
          ref={(node) => void (refs.current.message = node)}
          id="message"
          className="field__input field__input--area"
          rows={6}
          value={input.message}
          aria-required="true"
          aria-invalid={error("message") ? true : undefined}
          aria-describedby={describe("message", "message-meta")}
          onChange={(event) => set("message", event.target.value)}
        />
      </Field>

      <Field label="Your name (optional)" error={error("name")} id="name">
        <input
          ref={(node) => void (refs.current.name = node)}
          id="name"
          className="field__input"
          value={input.name}
          maxLength={80}
          autoComplete="name"
          aria-invalid={error("name") ? true : undefined}
          aria-describedby={describe("name")}
          onChange={(event) => set("name", event.target.value)}
        />
      </Field>

      <Field label="Your e-mail (optional)" hint="Only if you want a reply." error={error("email")} id="email">
        <input
          ref={(node) => void (refs.current.email = node)}
          id="email"
          className="field__input"
          type="email"
          inputMode="email"
          value={input.email}
          maxLength={254}
          autoComplete="email"
          aria-invalid={error("email") ? true : undefined}
          aria-describedby={describe("email", "email-hint")}
          onChange={(event) => set("email", event.target.value)}
        />
      </Field>

      {/* Bots fill every field they find. People never reach this one. */}
      <div className="hp" aria-hidden="true">
        <label>
          Leave this empty
          <input
            name="website"
            tabIndex={-1}
            autoComplete="off"
            value={input.website}
            onChange={(event) => set("website", event.target.value)}
          />
        </label>
      </div>

      <p className="form__privacy">
        What you write is e-mailed to the project owner and used only to answer you. Details are on the{" "}
        <Link href="/privacy">Privacy page</Link>.
      </p>
      <button type="submit" className="btn" disabled={sending} aria-busy={sending}>
        {sending ? "Sending…" : "Send message"}
      </button>
    </form>
  );
}

interface FieldProps {
  id: string;
  label: string;
  /** Guidance shown above the input. */
  hint?: string;
  /** A running note shown below the input, such as a character count. */
  meta?: string;
  error?: string | undefined;
  required?: boolean;
  children: React.ReactNode;
}

function Field({ id, label, hint, meta, error, required, children }: FieldProps) {
  return (
    <div className="field">
      <label htmlFor={id} className="field__label">
        {label}
        {required && <span className="field__req"> (required)</span>}
      </label>
      {hint && (
        <p className="field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {children}
      {error && (
        <p className="field__error" id={`${id}-error`}>
          {error}
        </p>
      )}
      {meta && (
        <p className="field__hint" id={`${id}-meta`}>
          {meta}
        </p>
      )}
    </div>
  );
}
