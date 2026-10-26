import { describe, expect, it } from "vitest";
import { checkoutSchema, normalizePhone, phone } from "./schemas";

describe("téléphone ivoirien", () => {
  it("normalise les écritures courantes", () => {
    expect(normalizePhone("+225 07 08 12 34 56")).toBe("0708123456");
    expect(normalizePhone("00225-05.44.21.87.90")).toBe("0544218790");
    expect(phone.parse("27 22 44 55 66")).toBe("2722445566"); // fixe
  });

  it("refuse les numéros invalides", () => {
    for (const bad of ["708123456", "07081234567", "+33 6 12 34 56 78", "1722445566"]) {
      expect(phone.safeParse(bad).success).toBe(false);
    }
  });
});

describe("formulaire de commande", () => {
  const valid = {
    customer_name: "Aya Kouassi",
    phone: "07 08 12 34 56",
    email: "",
    commune_id: "3",
    address_line: "Riviera 3, villa 12",
    landmark: "",
    accept_terms: true,
  };

  it("accepte une commande sans e-mail (invité)", () => {
    const out = checkoutSchema.parse(valid);
    expect(out.phone).toBe("0708123456");
    expect(out.commune_id).toBe(3);
  });

  it("exige les CGV et une commune", () => {
    const r = checkoutSchema.safeParse({ ...valid, accept_terms: false, commune_id: "" });
    expect(r.success).toBe(false);
    const fields = r.error?.issues.map((i) => i.path[0]);
    expect(fields).toEqual(expect.arrayContaining(["accept_terms", "commune_id"]));
  });
});
