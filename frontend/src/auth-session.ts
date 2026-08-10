import { User, AuthSession } from "./auth";

export const LOGIN_DISABLED_FOR_DEV = false;
export const RESTORE_LOGIN_SESSION_ON_REFRESH = false;
export const SESSION_USER_STORAGE_KEY = "dobedub.react.user.db-auth.v1";
export const LEGACY_SESSION_USER_STORAGE_KEYS = ["dobedub.react.user", "dobedub.react.user.auth"];
export const DEV_USER: User = { id: "dobedub", name: "장균은", role: "SUPER_ADMIN", permissions: ["admin:*"], isActive: true };

export function loadSessionUser(): User | null {
  clearLoginSession(RESTORE_LOGIN_SESSION_ON_REFRESH);
  if (LOGIN_DISABLED_FOR_DEV) {
    sessionStorage.setItem(SESSION_USER_STORAGE_KEY, JSON.stringify({ user: DEV_USER, accessToken: "" }));
    return DEV_USER;
  }
  if (!RESTORE_LOGIN_SESSION_ON_REFRESH) {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(SESSION_USER_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<AuthSession> & User;
    return parsed.user || parsed;
  } catch {
    return null;
  }
}

export function clearLoginSession(keepCurrent = false) {
  if (typeof sessionStorage !== "undefined") {
    [...LEGACY_SESSION_USER_STORAGE_KEYS, ...(keepCurrent ? [] : [SESSION_USER_STORAGE_KEY])]
      .forEach((key) => sessionStorage.removeItem(key));
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith("dobedub.react.user") && !(keepCurrent && key === SESSION_USER_STORAGE_KEY)) {
        sessionStorage.removeItem(key);
      }
    }
  }
  if (typeof localStorage !== "undefined") {
    for (let index = localStorage.length - 1; index >= 0; index -= 1) {
      const key = localStorage.key(index);
      if (key?.startsWith("dobedub.react.user")) {
        localStorage.removeItem(key);
      }
    }
  }
}
