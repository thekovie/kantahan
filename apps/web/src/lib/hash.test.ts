import { createHash, randomBytes } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sha256Fallback, sha256Hex } from "./hash";

const buffer = (text: string): ArrayBuffer => new TextEncoder().encode(text).buffer as ArrayBuffer;
const exact = (bytes: Uint8Array): ArrayBuffer => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;

afterEach(() => vi.unstubAllGlobals());

describe("sha256Fallback", () => {
  it.each([
    ["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    ["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],
    ["abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"],
  ])("matches the published test vector for %j", (text, expected) => {
    expect(sha256Fallback(buffer(text))).toBe(expected);
  });

  it("agrees with the platform for every length around a block boundary and for a large input", () => {
    for (let length = 0; length <= 200; length++) {
      const bytes = randomBytes(length);
      expect(sha256Fallback(exact(bytes))).toBe(createHash("sha256").update(bytes).digest("hex"));
    }
    const big = randomBytes(300_001);
    expect(sha256Fallback(exact(big))).toBe(createHash("sha256").update(big).digest("hex"));
  });
});

describe("sha256Hex", () => {
  it("uses the browser's SubtleCrypto when there is one", async () => {
    expect(await sha256Hex(buffer("abc"))).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });

  it("still verifies on a page without SubtleCrypto (plain http)", async () => {
    vi.stubGlobal("crypto", {});
    expect(await sha256Hex(buffer("abc"))).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });
});
