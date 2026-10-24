import { describe, expect, it, vi } from "vitest";
import { type ContactInput, checkContact, sendContact } from "./contact";

const valid: ContactInput = {
  type: "correction",
  message: "Song 00589 lists the wrong artist.",
  email: "someone@example.org",
  name: "A Person",
  reference: "Reyna, 00589",
  website: "",
};

const reply = (status: number, body: unknown = {}, headers: Record<string, string> = {}) =>
  vi.fn(async () => new Response(JSON.stringify(body), { status, headers }));

describe("checkContact", () => {
  it("accepts a complete form and a form with only the required parts", () => {
    expect(checkContact(valid)).toEqual({});
    expect(checkContact({ ...valid, email: "", name: "", reference: "" })).toEqual({});
  });

  it.each([
    [{ type: "" as const }, "type"],
    [{ message: "short" }, "message"],
    [{ message: "x".repeat(2001) }, "message"],
    [{ message: "   \n  " }, "message"],
    [{ email: "nope" }, "email"],
  ])("flags %j", (patch, field) => {
    expect(Object.keys(checkContact({ ...valid, ...patch }))).toContain(field);
  });
});

describe("sendContact", () => {
  it("posts JSON without credentials and reports success on 202", async () => {
    const fetchFn = reply(202, { ok: true });
    expect(await sendContact(valid, { fetchFn: fetchFn as unknown as typeof fetch })).toEqual({ status: "sent" });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/contact");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("omit");
    expect(JSON.parse(String(init.body))).toMatchObject({ type: "correction", website: "" });
  });

  it("trims what it sends and sends nothing when the form is invalid", async () => {
    const fetchFn = reply(202);
    await sendContact({ ...valid, message: "  Enough characters here.  " }, { fetchFn: fetchFn as unknown as typeof fetch });
    expect(JSON.parse(String((fetchFn.mock.calls[0] as unknown as [string, RequestInit])[1].body)).message).toBe("Enough characters here.");
    const never = reply(202);
    const result = await sendContact({ ...valid, message: "" }, { fetchFn: never as unknown as typeof fetch });
    expect(result.status).toBe("invalid");
    expect(never).not.toHaveBeenCalled();
  });

  it("maps server field errors, rate limits, outages and a lost connection", async () => {
    const f = (fn: ReturnType<typeof reply>) => ({ fetchFn: fn as unknown as typeof fetch });
    expect(await sendContact(valid, f(reply(422, { ok: false, fields: { email: "Bad", extra: "x" } })))).toEqual({
      status: "invalid",
      fields: { email: "Bad" },
    });
    expect(await sendContact(valid, f(reply(429, {}, { "Retry-After": "130" })))).toEqual({ status: "slow-down", minutes: 3 });
    expect(await sendContact(valid, f(reply(429)))).toEqual({ status: "slow-down", minutes: 60 });
    expect(await sendContact(valid, f(reply(503)))).toEqual({ status: "unavailable" });
    expect(await sendContact(valid, f(reply(422, "garbage")))).toEqual({ status: "unavailable" });
    expect(await sendContact(valid, f(reply(403)))).toEqual({ status: "unavailable" });
    const offline = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    expect(await sendContact(valid, f(offline as unknown as ReturnType<typeof reply>))).toEqual({ status: "offline" });
  });
});
