import { useSyncExternalStore } from "react";

export type UserRole = "nurse" | "doctor" | "admin";

export interface AuthUser {
  name: string;
  role: UserRole;
  email: string;
  token: string;
}

const API = "http://localhost:8000/api/v1/auth";
const TOKEN_KEY = "triage_token";

// ── Active session ────────────────────────────────────────────────────────────
let _user: AuthUser | null = (() => {
  // Restore session from localStorage on page load
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    if (raw) return JSON.parse(raw) as AuthUser;
  } catch { /* ignore */ }
  return null;
})();

let _listeners = new Set<() => void>();
function notify() { _listeners.forEach((l) => l()); }
function subscribe(cb: () => void) { _listeners.add(cb); return () => { _listeners.delete(cb); }; }
function getSnapshot() { return _user; }

function setUser(u: AuthUser | null) {
  _user = u;
  if (u) localStorage.setItem(TOKEN_KEY, JSON.stringify(u));
  else localStorage.removeItem(TOKEN_KEY);
  notify();
}

// ── API calls ─────────────────────────────────────────────────────────────────
export async function apiRegister(
  name: string, email: string, role: UserRole, password: string
): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(`${API}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, role, password }),
    });
    if (res.status === 409) return { ok: false, error: "An account with this email already exists." };
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return { ok: false, error: data.detail || "Registration failed." };
    }
    const data = await res.json();
    setUser({ name: data.name, role: data.role as UserRole, email: data.email, token: data.token });
    return { ok: true };
  } catch {
    return { ok: false, error: "Cannot reach server. Is the backend running?" };
  }
}

export async function apiLogin(
  email: string, password: string
): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.status === 401) return { ok: false, error: "Invalid email or password." };
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return { ok: false, error: data.detail || "Login failed." };
    }
    const data = await res.json();
    setUser({ name: data.name, role: data.role as UserRole, email: data.email, token: data.token });
    return { ok: true };
  } catch {
    return { ok: false, error: "Cannot reach server. Is the backend running?" };
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useAuth() {
  const user = useSyncExternalStore(subscribe, getSnapshot);
  return {
    user,
    logout: () => setUser(null),
  };
}
