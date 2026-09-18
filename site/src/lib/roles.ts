import type { Role } from "../types";

export function isGlobalAdmin(role?: Role | string | null): boolean {
  return role === "adm";
}

export function isDev(role?: Role | string | null): boolean {
  return role === "dev";
}

export function canManageUsers(role?: Role | string | null): boolean {
  return role === "adm" || role === "adm_local";
}

export function canManageConfig(role?: Role | string | null): boolean {
  return role === "adm";
}

export function canSeeAcesso(role?: Role | string | null): boolean {
  return role === "dev";
}

export function canSeeFilas(role?: Role | string | null): boolean {
  return role === "dev";
}

export function canSeeLogs(_role?: Role | string | null): boolean {
  return true;
}

export function roleLabel(role?: Role | string | null): string {
  switch (role) {
    case "adm":
      return "Admin";
    case "adm_local":
      return "Adm local";
    case "dev":
      return "Dev";
    default:
      return "Usuário";
  }
}

export function creatableRoles(actor?: Role | string | null): Role[] {
  if (actor === "adm") return ["usuario", "adm_local", "adm", "dev"];
  if (actor === "adm_local") return ["usuario", "adm_local"];
  return [];
}
