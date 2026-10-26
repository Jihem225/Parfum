import { expect, test } from "@playwright/test";

// Mobile money avec le prestataire de simulation (PAYMENT_PROVIDER=simulation, jamais en production).

test("mobile money : refus, nouvel essai, paiement puis suivi", async ({ page }) => {
  await page.goto("/parfums/ambre-lagune");
  await page.getByRole("button", { name: /50 ml/ }).click();
  await page.getByRole("button", { name: "Ajouter au panier" }).click();
  await expect(page.getByText("Ajouté au panier")).toBeVisible();

  await page.goto("/commande");
  await page.getByLabel("Nom et prénom").fill("Client Mobile");
  await page.getByLabel(/^Téléphone/).fill("07 08 12 34 56");
  await page.getByLabel("Commune").selectOption({ index: 1 }); // Cocody : 1 500 FCFA
  await page.getByLabel(/^Adresse/).fill("Riviera 3, villa 12");
  await page.getByRole("radio", { name: /Mobile money/ }).check();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: /^Payer 39\s500\sFCFA$/ }).click(); // 38 000 + 1 500

  await expect(page).toHaveURL(/\/paiement\/simulation/);
  await expect(page.getByText("Simulation : aucun argent réel n'est débité.")).toBeVisible();
  await page.getByRole("button", { name: "Refuser le paiement" }).click();
  await expect(page.getByRole("heading", { name: "Paiement en attente" })).toBeVisible();
  const number = (await page.getByText(/^PP-\d+$/).textContent()) ?? "";

  await page.getByRole("button", { name: "Réessayer le paiement" }).click();
  await page.getByRole("button", { name: "Confirmer le paiement" }).click();
  await expect(page).toHaveURL(/\/commande\/confirmee.*paye=1/);
  await expect(page.getByText("Paiement reçu : votre commande est confirmée.")).toBeVisible();
  await expect(page.getByText(number, { exact: true })).toBeVisible();

  await page.locator('a[href^="/suivi?numero="]').click();
  await page.getByLabel("Téléphone").filter({ visible: true }).fill("0708123456");
  await page.getByRole("button", { name: "Suivre" }).click();
  await expect(page.getByRole("heading", { name: number })).toBeVisible();
  await expect(page.getByText("Total payé par mobile money")).toBeVisible();
});

test("lien de paiement falsifié : refusé sans rien révéler", async ({ page }) => {
  await page.goto("/commande/paiement?numero=PP-10001&t=jeton-invente");
  await expect(page.getByText("Commande introuvable.")).toBeVisible();
});
