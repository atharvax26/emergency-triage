import { useState, useEffect, useSyncExternalStore } from "react";

export type UserRole = "nurse" | "doctor";

export interface AuthUser {
  name: string;
  role: UserRole;
}

let _user: AuthUser | null = null;
let _listeners = new Set<() => void>();

function notify() {
  _listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  _listeners.add(listener);
  return () => { _listeners.delete(listener); };
}

function getSnapshot() {
  return _user;
}

export function useAuth() {
  const user = useSyncExternalStore(subscribe, getSnapshot);

  return {
    user,
    login: (name: string, role: UserRole) => {
      _user = { name, role };
      notify();
    },
    logout: () => {
      _user = null;
      notify();
    },
  };
}
