import { expect, test } from "@playwright/test";

// Parcours sur le catalogue d'exemple (backend/app/scripts/seed_demo.py, données fictives).

test("l'accueil mène au catalogue", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Projet Parfums/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Des sillages");
  await page.getByRole("link", { name: "Découvrir les parfums" }).click();
  await expect(page.getByRole("heading", { name: "Parfums" })).toBeVisible();
  await expect(page.getByText("Ambre Lagune").first()).toBeVisible();
});

test("commande sans compte, du panier au suivi", async ({ page }) => {
  await page.goto("/parfums/ambre-lagune");
  await page.getByRole("button", { name: /30 ml/ }).click();
  await page.getByRole("button", { name: "Ajouter au panier" }).click();
  await expect(page.getByText("Ajouté au panier")).toBeVisible();

  await page.goto("/panier");
  await expect(page.getByRole("link", { name: "Ambre Lagune" })).toBeVisible();
  await page.getByRole("link", { name: "Commander" }).click();

  await page.getByLabel("Nom et prénom").fill("Client Test");
  await page.getByLabel(/^Téléphone/).fill("07 08 12 34 56");
  await page.getByLabel("Commune").selectOption({ index: 1 }); // Cocody : 1 500 FCFA
  await page.getByLabel(/^Adresse/).fill("Riviera 3, villa 12");
  await expect(page.getByText(/26\s500\sFCFA/).last()).toBeVisible(); // 25 000 + 1 500

  await page.getByRole("button", { name: "Valider la commande" }).click();
  await expect(page.getByText("Vous devez accepter les conditions générales de vente.")).toBeVisible();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Valider la commande" }).click();

  await expect(page).toHaveURL(/\/commande\/confirmee/);
  const number = (await page.getByText(/^PP-\d+$/).textContent()) ?? "";
  expect(number).toMatch(/^PP-\d+$/);
  await page.getByRole("link", { name: "Suivre ma commande" }).last().click();
  await page.getByLabel("Téléphone").fill("0708123456");
  await page.getByRole("button", { name: "Suivre" }).click();
  await expect(page.getByRole("heading", { name: number })).toBeVisible();
  await expect(page.getByText("En attente de confirmation").first()).toBeVisible();
});

test("suivi : un mauvais couple numéro / téléphone reste générique", async ({ page }) => {
  await page.goto("/suivi?numero=PP-1");
  await page.getByLabel("Téléphone").fill("0101010101");
  await page.getByRole("button", { name: "Suivre" }).click();
  await expect(page.getByText("Aucune commande ne correspond à ce numéro et ce téléphone.")).toBeVisible();
});
