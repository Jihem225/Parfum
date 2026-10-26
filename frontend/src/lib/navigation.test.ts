import { describe, expect, it } from "vitest";
import { homeFor, safeNext } from "./navigation";

describe("navigation", () => {
  it("n'accepte que des chemins internes comme destination", () => {
    expect(safeNext("/commande")).toBe("/commande");
    expect(safeNext("//pirate.example")).toBeUndefined();
    expect(safeNext("https://pirate.example")).toBeUndefined();
    expect(safeNext(["/a"])).toBeUndefined();
  });

  it("envoie chaque rôle dans son espace", () => {
    expect(homeFor("CUSTOMER")).toBe("/compte");
    expect(homeFor("COURIER")).toBe("/livreur");
    expect(homeFor("MANAGER")).toBe("/admin");
    expect(homeFor("OWNER")).toBe("/admin");
  });
});
