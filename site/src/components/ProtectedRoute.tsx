import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth";

interface ProtectedRouteProps {
  children: ReactNode;
  adminOnly?: boolean;
}

export function ProtectedRoute({ children, adminOnly = false }: ProtectedRouteProps) {
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

  return <>{children}</>;
}
