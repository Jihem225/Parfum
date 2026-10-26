import { expect, type Page } from "@playwright/test";

/** Commande passée par l'API (dans la session de `page`) : 1 × Vétiver Plateau 50 ml. Avec
 * `paid`, réglée par mobile money (prestataire de simulation). */
export async function placeOrder(page: Page, { paid = false } = {}): Promise<string> {
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
      payment_method: paid ? "MOBILE_MONEY" : "CASH_ON_DELIVERY",
    },
  });
  expect(order.status()).toBe(201);
  const { number, payment_token } = await order.json();
  if (paid) {
    const payment = await page.request.post(`/api/v1/payments/simulation/${number}`, { headers, data: { token: payment_token, paid: true } });
    expect((await payment.json()).order_status).toBe("CONFIRMEE");
  }
  return number;
}
