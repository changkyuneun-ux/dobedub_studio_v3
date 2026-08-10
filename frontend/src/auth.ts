// E-01: Shared auth/session types and permission-check helpers.
// Extracted out of main.tsx so components outside the app entry file (e.g.
// components/AppShell.tsx) can use the same permission logic without
// creating a circular import (main.tsx -> AppShell -> main.tsx). Behavior is
// unchanged from the original in-file definitions - this is a pure move.

export type User = {
  id: string;
  name: string;
  email?: string | null;
  role?: string;
  permissions?: string[];
  rolePermissionCodes?: string[];
  extraPermissionCodes?: string[];
  effectivePermissionCodes?: string[];
  isActive?: boolean;
};

export type AuthSession = {
  user: User;
  accessToken: string;
  tokenType?: string;
  expiresAt?: string;
};

export function userPermissionCodes(user: User | null): string[] {
  if (!user) {
    return [];
  }
  return Array.from(new Set([
    ...(user.effectivePermissionCodes || []),
    ...(user.permissions || []),
    ...(user.rolePermissionCodes || []),
    ...(user.extraPermissionCodes || [])
  ].map((item) => String(item || "").trim()).filter(Boolean)));
}

export function canUse(user: User | null, permission: string): boolean {
  const permissions = userPermissionCodes(user);
  if (permissions.includes("admin:*")) {
    return true;
  }
  if (permissions.includes(permission)) {
    return true;
  }
  const domain = permission.split(":", 1)[0];
  return permissions.includes(`${domain}:*`);
}

export function canUseAny(user: User | null, permissions: string[]): boolean {
  return permissions.some((permission) => canUse(user, permission));
}
