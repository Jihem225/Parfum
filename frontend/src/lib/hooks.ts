"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "./api";
import type { Cart, User } from "./types";

/** Utilisateur connecté, ou null. */
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
  });
}

export function useCart() {
  return useQuery({ queryKey: ["cart"], queryFn: () => api<Cart>("/cart") });
}

/** Mutations du panier : la réponse est le panier à jour, posée directement dans le cache. */
export function useCartMutations() {
  const qc = useQueryClient();
  const onSuccess = (cart: Cart) => qc.setQueryData(["cart"], cart);
  return {
    add: useMutation({
      mutationFn: (v: { variant_id: number; quantity: number }) => api<Cart>("/cart/items", { json: v }),
      onSuccess,
    }),
    update: useMutation({
      mutationFn: (v: { variant_id: number; quantity: number }) =>
        api<Cart>(`/cart/items/${v.variant_id}`, { method: "PATCH", json: { quantity: v.quantity } }),
      onSuccess,
    }),
    remove: useMutation({
      mutationFn: (variantId: number) => api<Cart>(`/cart/items/${variantId}`, { method: "DELETE" }),
      onSuccess,
    }),
  };
}

/** Après connexion ou déconnexion, tout ce qui dépend de la session est relu. */
export function useSessionReset() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries();
}
