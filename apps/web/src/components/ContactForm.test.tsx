import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";
import { describe, expect, it, vi } from "vitest";
import type { ContactInput, ContactResult } from "../lib/contact";
import { ContactForm } from "./ContactForm";

function setup(result: ContactResult = { status: "sent" }) {
  const send = vi.fn<(input: ContactInput) => Promise<ContactResult>>(async () => result);
  const { hook } = memoryLocation({ path: "/rights" });
  render(
    <Router hook={hook}>
      <ContactForm send={send} />
    </Router>,
  );
  return { send, user: userEvent.setup() };
}

async function fillValid(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("radio", { name: "Correct a number, title or artist" }));
  await user.type(screen.getByLabelText(/^Message/), "Song 00589 lists the wrong artist.");
}

describe("ContactForm", () => {
  it("sends what was typed, then thanks the visitor and moves focus to the thanks", async () => {
    const { send, user } = setup();
    await fillValid(user);
    await user.type(screen.getByLabelText(/Your e-mail/), "someone@example.org");
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0]?.[0]).toMatchObject({ type: "correction", email: "someone@example.org", website: "" });
    const heading = await screen.findByRole("heading", { name: "Message sent" });
    expect(heading).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Send another message" }));
    expect(await screen.findByLabelText(/^Message/)).toHaveValue("");
  });

  it("shows what is wrong next to the field and moves focus to the first one, without sending", async () => {
    const { send, user } = setup();
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(send).not.toHaveBeenCalled();
    expect(screen.getByText("Choose what this is about.")).toBeInTheDocument();
    expect(screen.getByText(/Write at least 10 characters/)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Remove an entry" })).toHaveFocus();
    await user.click(screen.getByRole("radio", { name: "Something else" }));
    expect(screen.queryByText("Choose what this is about.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(screen.getByLabelText(/^Message/)).toHaveFocus();
    expect(screen.getByLabelText(/^Message/)).toHaveAttribute("aria-invalid", "true");
  });

  it("keeps the message and explains a rate limit, an outage and a lost connection", async () => {
    for (const [result, text] of [
      [{ status: "slow-down", minutes: 5 }, /Try again in about 5 minutes/],
      [{ status: "unavailable" }, /could not be sent right now/],
      [{ status: "offline" }, /Your message is still here/],
    ] as const) {
      const { user } = setup(result);
      await fillValid(user);
      await user.click(screen.getByRole("button", { name: "Send message" }));
      expect(await screen.findByRole("alert")).toHaveTextContent(text);
      expect(screen.getByLabelText(/^Message/)).toHaveValue("Song 00589 lists the wrong artist.");
      document.body.innerHTML = "";
    }
  });

  it("shows the server's field messages", async () => {
    const { user } = setup({ status: "invalid", fields: { email: "Enter a valid e-mail address, or leave it empty." } });
    await fillValid(user);
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText(/Enter a valid e-mail address/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Your e-mail/)).toHaveFocus();
  });

  it("disables the button while sending so a double tap sends once", async () => {
    let finish!: (r: ContactResult) => void;
    const send = vi.fn(() => new Promise<ContactResult>((resolve) => (finish = resolve)));
    const { hook } = memoryLocation({ path: "/rights" });
    render(
      <Router hook={hook}>
        <ContactForm send={send} />
      </Router>,
    );
    const user = userEvent.setup();
    await fillValid(user);
    const button = screen.getByRole("button", { name: "Send message" });
    await user.click(button);
    expect(await screen.findByRole("button", { name: "Sending…" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Sending…" }));
    expect(send).toHaveBeenCalledTimes(1);
    finish({ status: "sent" });
    await waitFor(() => expect(screen.getByRole("heading", { name: "Message sent" })).toBeInTheDocument());
  });

  it("has a honeypot that people cannot reach: hidden from assistive tech and the tab order", () => {
    setup();
    const trap = document.querySelector<HTMLInputElement>('input[name="website"]');
    expect(trap).not.toBeNull();
    expect(trap?.tabIndex).toBe(-1);
    expect(trap?.closest("[aria-hidden='true']")).not.toBeNull();
    expect(screen.queryByRole("textbox", { name: /Leave this empty/ })).not.toBeInTheDocument();
  });

  it("tells visitors where their message goes and links the privacy page", () => {
    setup();
    expect(screen.getByText(/e-mailed to the project owner/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy page" })).toHaveAttribute("href", "/privacy");
  });
});
