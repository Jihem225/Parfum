import { expect, test, type Page } from "@playwright/test";
import { placeOrder } from "./order";
import { totp } from "./totp";

// Comptes créés par seed_demo quand SEED_STAFF_PASSWORD / SEED_MANAGER_TOTP_SECRET sont fournis (CI).
const PASSWORD = process.env.SEED_STAFF_PASSWORD ?? "";
const SECRET = process.env.SEED_MANAGER_TOTP_SECRET ?? "";
test.skip(!PASSWORD || !SECRET, "comptes de test non configurés");

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
