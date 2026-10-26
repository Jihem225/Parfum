import { describe, expect, it } from "vitest";
import { ApiError, errorMessage } from "./api";

describe("erreurs de l'API", () => {
  const validation = new ApiError(422, "VALIDATION_ERROR", "Certaines données sont invalides.", [
    { field: "phone", message: "Numéro ivoirien attendu : 10 chiffres." },
    { field: "phone", message: "doublon ignoré" },
    { field: "email", message: "Adresse e-mail invalide." },
  ]);

  it("expose les erreurs par champ (la première par champ)", () => {
    expect(validation.fieldErrors()).toEqual({
      phone: "Numéro ivoirien attendu : 10 chiffres.",
      email: "Adresse e-mail invalide.",
    });
  });

  it("donne un message lisible", () => {
    expect(errorMessage(validation)).toBe("Numéro ivoirien attendu : 10 chiffres.");
    expect(errorMessage(new ApiError(409, "MAX_QUANTITY", "5 unités maximum par contenance."))).toBe("5 unités maximum par contenance.");
    expect(errorMessage(new TypeError("x"))).toBe("Une erreur est survenue. Réessayez.");
  });
});
