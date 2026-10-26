import { expect, test, type Page } from "@playwright/test";
import { totp } from "./totp";

// Comptes créés par seed_demo quand SEED_STAFF_PASSWORD / SEED_MANAGER_TOTP_SECRET sont fournis (CI).
const PASSWORD = process.env.SEED_STAFF_PASSWORD ?? "";
const SECRET = process.env.SEED_MANAGER_TOTP_SECRET ?? "";
test.skip(!PASSWORD || !SECRET, "comptes de test non configurés");

async function placeOrder(page: Page): Promise<string> {
  await page.goto("/"); // pose le cookie CSRF
  const csrf = (await page.context().cookies()).find((c) => c.name === "csrf")?.value ?? "";
  const headers = { "X-CSRF-Token": csrf };
  const product = await (await page.request.get("/api/v1/catalog/products/vetiver-plateau")).json();
  const communes = await (await page.request.get("/api/v1/delivery/communes")).json();
  await page.request.post("/api/v1/cart/items", { headers, data: { variant_id: product.variants[0].id, quantity: 1 } });
  const preview = await (await page.request.post("/api/v1/checkout/preview", { headers, data: { commune_id: communes[0].id } })).json();
  const order = await page.request.post("/api/v1/orders", {
    headers,
    data: {
      customer_name: "Client Parcours",
      phone: "0708123456",
      commune_id: communes[0].id,
      address_line: "Riviera 3, villa 12",
      accept_terms: true,
      expected_total: preview.total,
      idempotency_key: crypto.randomUUID(),
    },
  });
  expect(order.status()).toBe(201);
  return (await order.json()).number;
}

async function login(page: Page, path: string, email: string, withCode: boolean) {
  await page.goto(path);
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Mot de passe").fill(PASSWORD);
  await page.getByRole("button", { name: "Se connecter" }).click();
  if (withCode) {
    await page.getByLabel("Code de double authentification").fill(totp(SECRET));
    await page.getByRole("button", { name: "Se connecter" }).click();
  }
}

test("commande traitée, livrée, encaissée puis remise en caisse", async ({ browser }) => {
  const customer = await browser.newPage();
  const number = await placeOrder(customer);

  const admin = await browser.newPage();
  admin.on("dialog", (d) => d.accept());
  await login(admin, "/admin/connexion", "gestion-e2e@exemple.com", true);
  await expect(admin.getByRole("heading", { name: "Tableau de bord" })).toBeVisible();

  await admin.goto(`/admin/commandes/${number}`);
  await admin.getByRole("button", { name: "Confirmée" }).click();
  await admin.getByRole("button", { name: "Passer en préparation" }).click();
  await admin.getByLabel("Livreur").selectOption({ index: 1 });
  await admin.getByRole("button", { name: "Confier au livreur" }).click();
  await expect(admin.getByText("Livreur : Livreur Test")).toBeVisible();

  const courier = await browser.newPage();
  await login(courier, "/livreur/connexion", "livreur-e2e@exemple.com", false);
  const card = courier.locator("li", { hasText: number });
  await card.getByRole("button", { name: "Livrée", exact: true }).click();
  await card.getByRole("checkbox").check();
  await card.getByRole("button", { name: "Livrée et encaissée" }).click();
  await expect(courier.locator("li", { hasText: number })).toHaveCount(0);

  await admin.goto("/admin/encaissements");
  await expect(admin.getByRole("link", { name: new RegExp(number) })).toBeVisible();
  await admin.getByRole("button", { name: "Enregistrer la remise" }).first().click();
  await expect(admin.getByText("Aucun livreur ne détient d'espèces à remettre.")).toBeVisible();
  await expect(admin.getByRole("cell", { name: new RegExp(number) })).toBeVisible();
});
