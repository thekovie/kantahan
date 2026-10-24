import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import { cleanup, configure } from "@testing-library/react";
import { webcrypto } from "node:crypto";
import { afterEach, vi } from "vitest";

// jsdom may not expose SubtleCrypto; the app verifies downloads with it.
if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, "crypto", { value: webcrypto });

// Waits for async UI are generous so a busy machine (or CI runner) does not make tests flaky.
configure({ asyncUtilTimeout: 4000 });

afterEach(() => {
  cleanup();
  try {
    localStorage.clear();
  } catch {
    // jsdom always provides localStorage; this guards tests that replace it
  }
});

// jsdom has no <dialog> modal support.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}

// jsdom does not implement scrolling.
window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
