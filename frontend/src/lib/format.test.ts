import { describe, expect, it } from "vitest";
import { formatFCFA } from "./format";

describe("formatFCFA", () => {
  it("sépare les milliers et ajoute la devise", () => {
    expect(formatFCFA(61500)).toBe("61 500 FCFA");
    expect(formatFCFA(0)).toBe("0 FCFA");
    expect(formatFCFA(1250000)).toBe("1 250 000 FCFA");
  });

  it("refuse les montants non entiers", () => {
    expect(() => formatFCFA(1500.5)).toThrow();
    expect(() => formatFCFA(Number.NaN)).toThrow();
  });
});
