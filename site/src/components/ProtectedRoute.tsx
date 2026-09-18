import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth";
import {
  canManageConfig,
  canManageUsers,
  canSeeAcesso,
  canSeeLogs,
} from "../lib/roles";

interface ProtectedRouteProps {
  children: ReactNode;
  adminOnly?: boolean;
  usersManagerOnly?: boolean;
  configOnly?: boolean;
  acessoOnly?: boolean;
  logsAllowed?: boolean;
}

export function ProtectedRoute({
  children,
  adminOnly = false,
  usersManagerOnly = false,
  configOnly = false,
  acessoOnly = false,
  logsAllowed = false,
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="centered">Carregando...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && user.role !== "adm") {
    return <Navigate to="/" replace />;
  }
  if (usersManagerOnly && !canManageUsers(user.role)) {
    return <Navigate to="/" replace />;
  }
  if (configOnly && !canManageConfig(user.role)) {
    return <Navigate to="/" replace />;
  }
  if (acessoOnly && !canSeeAcesso(user.role)) {
    return <Navigate to="/" replace />;
  }
  if (logsAllowed && !canSeeLogs(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
