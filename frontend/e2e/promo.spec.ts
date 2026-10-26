import { expect, test } from "@playwright/test";

// Code d'exemple BIENVENUE10 (seed_demo) : 10 % des articles, plafonné à 5 000 FCFA, 1 fois par téléphone.

test("code promo : refusé puis accepté, remise jusqu'au suivi", async ({ page }, testInfo) => {
  const phone = testInfo.project.name === "mobile" ? "0708000001" : "0708000002"; // 1 fois par numéro
  await page.goto("/parfums/neroli-d-assinie");
  await page.getByRole("button", { name: /30 ml/ }).click();
  await page.getByRole("button", { name: "Ajouter au panier" }).click();
  await expect(page.getByText("Ajouté au panier")).toBeVisible();

  await page.goto("/commande");
  await page.getByLabel("Nom et prénom").fill("Client Promo");
  await page.getByLabel(/^Téléphone/).fill(phone);
  await page.getByLabel("Commune").selectOption({ index: 1 }); // Cocody : 1 500 FCFA
  await page.getByLabel(/^Adresse/).fill("Riviera 3, villa 12");
  await expect(page.getByText(/23\s500\sFCFA/).last()).toBeVisible(); // 22 000 + 1 500

  await page.getByLabel("Code promo").fill("FAUXCODE");
  await page.getByRole("button", { name: "Appliquer" }).click();
  await expect(page.getByText("Ce code promo n'est pas valable.")).toBeVisible();
  await page.getByLabel("Code promo").fill("bienvenue10");
  await page.getByRole("button", { name: "Appliquer" }).click();
  await expect(page.getByText("Code BIENVENUE10")).toBeVisible();
  await expect(page.getByText(/−2\s200\sFCFA/)).toBeVisible();
  await expect(page.getByText(/21\s300\sFCFA/).last()).toBeVisible(); // 22 000 − 2 200 + 1 500

  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Valider la commande" }).click();
  await expect(page).toHaveURL(/\/commande\/confirmee/);
  const number = (await page.getByText(/^PP-\d+$/).textContent()) ?? "";
  await page.locator('a[href^="/suivi?numero="]').click();
  await page.getByLabel("Téléphone").filter({ visible: true }).fill(phone);
  await page.getByRole("button", { name: "Suivre" }).click();
  await expect(page.getByRole("heading", { name: number })).toBeVisible();
  await expect(page.getByText("Code BIENVENUE10")).toBeVisible();
  await expect(page.getByText(/21\s300\sFCFA/).last()).toBeVisible();
});
