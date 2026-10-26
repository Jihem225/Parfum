import { expect, test } from "@playwright/test";

test("création de compte, adresse, déconnexion puis connexion", async ({ page }) => {
  const email = `client-${Date.now()}-${Math.floor(Math.random() * 1e6)}@exemple.com`;
  await page.goto("/compte/inscription");
  await page.getByLabel("Nom et prénom").fill("Aya Kouassi");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Téléphone").fill("07 08 12 34 56");
  await page.getByLabel(/^Mot de passe/).fill("motdepasse-solide");
  await page.getByRole("button", { name: "Créer mon compte" }).click();
  await expect(page.getByRole("heading", { name: "Bonjour Aya" })).toBeVisible();

  await page.getByRole("link", { name: "Mes adresses" }).click();
  await page.getByLabel("Destinataire").fill("Aya Kouassi");
  await page.getByLabel("Téléphone").fill("0708123456");
  await page.getByLabel("Commune").selectOption({ index: 1 });
  await page.getByLabel(/^Adresse$/).fill("Riviera 3, villa 12");
  await page.getByRole("button", { name: "Ajouter" }).click();
  await expect(page.getByText("Par défaut")).toBeVisible();

  await page.getByRole("button", { name: "Se déconnecter" }).click();
  await page.goto("/compte/commandes");
  await expect(page).toHaveURL(/\/compte\/connexion\?suite=/);
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Mot de passe").fill("motdepasse-solide");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { name: "Mes commandes" })).toBeVisible();
});

test("connexion refusée avec un mauvais mot de passe", async ({ page }) => {
  await page.goto("/compte/connexion");
  await page.getByLabel("E-mail").fill("personne@exemple.com");
  await page.getByLabel("Mot de passe").fill("mauvais-mot-de-passe");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByText("E-mail ou mot de passe incorrect.")).toBeVisible();
});
