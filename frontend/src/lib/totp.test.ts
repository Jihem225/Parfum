import { describe, expect, it } from "vitest";
import { totp } from "../../e2e/totp";

describe("aide TOTP des tests E2E", () => {
  it("respecte le vecteur de test de la RFC 6238 (SHA-1)", () => {
    // Clé « 12345678901234567890 » en base32, instant 59 s → 94287082 (8 chiffres) → 287082.
    expect(totp("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 59_000)).toBe("287082");
  });
});
