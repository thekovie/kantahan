export type ContactKind = "removal" | "correction" | "other";
export type ContactField = "type" | "message" | "email" | "name" | "reference";

export interface ContactInput {
  type: ContactKind | "";
  message: string;
  email: string;
  name: string;
  reference: string;
  /** Hidden field that only a script fills in; it is sent as is and ignored by the server. */
  website: string;
}

export type ContactResult =
  | { status: "sent" }
  | { status: "invalid"; fields: Partial<Record<ContactField, string>> }
  | { status: "slow-down"; minutes: number }
  | { status: "offline" }
  | { status: "unavailable" };

export const CONTACT_URL: string = import.meta.env.VITE_CONTACT_URL ?? "/api/contact";
export const MESSAGE_MIN = 10;
export const MESSAGE_MAX = 2000;
const EMAIL_SHAPE = /^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$/;
const FIELDS: readonly ContactField[] = ["type", "message", "email", "name", "reference"];

/** The same checks the server makes, so mistakes are caught before anything is sent. */
export function checkContact(input: ContactInput): Partial<Record<ContactField, string>> {
  const fields: Partial<Record<ContactField, string>> = {};
  if (!input.type) fields.type = "Choose what this is about.";
  const length = input.message.trim().length;
  if (length < MESSAGE_MIN) fields.message = `Write at least ${MESSAGE_MIN} characters.`;
  else if (length > MESSAGE_MAX) fields.message = `Keep it under ${MESSAGE_MAX.toLocaleString("en-PH")} characters.`;
  if (input.email.trim() && !EMAIL_SHAPE.test(input.email.trim())) {
    fields.email = "Enter a valid e-mail address, or leave it empty.";
  }
  return fields;
}

function serverFields(body: unknown): Partial<Record<ContactField, string>> {
  const raw = typeof body === "object" && body !== null ? (body as { fields?: unknown }).fields : undefined;
  const out: Partial<Record<ContactField, string>> = {};
  if (typeof raw === "object" && raw !== null) {
    for (const key of FIELDS) {
      const value = (raw as Record<string, unknown>)[key];
      if (typeof value === "string") out[key] = value;
    }
  }
  return out;
}

export async function sendContact(
  input: ContactInput,
  deps: { fetchFn?: typeof fetch; url?: string } = {},
): Promise<ContactResult> {
  const found = checkContact(input);
  if (Object.keys(found).length > 0) return { status: "invalid", fields: found };
  const payload = {
    type: input.type,
    message: input.message.trim(),
    email: input.email.trim(),
    name: input.name.trim(),
    reference: input.reference.trim(),
    website: input.website,
  };
  let response: Response;
  try {
    response = await (deps.fetchFn ?? fetch)(deps.url ?? CONTACT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "omit",
    });
  } catch {
    return { status: "offline" };
  }
  if (response.status === 202) return { status: "sent" };
  if (response.status === 429) {
    const seconds = Number(response.headers.get("Retry-After")) || 3600;
    return { status: "slow-down", minutes: Math.max(1, Math.ceil(seconds / 60)) };
  }
  if (response.status === 422) {
    const fields = serverFields(await response.json().catch(() => null));
    return Object.keys(fields).length > 0 ? { status: "invalid", fields } : { status: "unavailable" };
  }
  return { status: "unavailable" };
}
