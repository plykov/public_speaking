"use client";

const KEY = "cadence_user_id";

export function getStoredUserId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setStoredUserId(id: string): void {
  window.localStorage.setItem(KEY, id);
}

export function clearStoredUserId(): void {
  window.localStorage.removeItem(KEY);
}
