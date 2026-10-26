import { expect, test } from "@playwright/test";

test("la page d'accueil s'affiche et joint l'API", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Projet Parfums/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("API : connectée")).toBeVisible();
});
