import { NavLink, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth";
import {
  canManageConfig,
  canManageUsers,
  canSeeAcesso,
  canSeeLogs,
  roleLabel,
} from "../lib/roles";
import { BrandLogo } from "./BrandLogo";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <BrandLogo />
          <nav>
            <NavLink to="/" end>
              Emitir Nota
            </NavLink>
            <NavLink to="/dashboard">Dashboard</NavLink>
            <NavLink to="/destinatarios">Destinatários</NavLink>
            {canManageUsers(user?.role) && <NavLink to="/usuarios">Usuários</NavLink>}
            {canSeeLogs(user?.role) && <NavLink to="/logs">Logs</NavLink>}
            {canSeeAcesso(user?.role) && <NavLink to="/acesso">Auditoria</NavLink>}
            {canManageConfig(user?.role) && (
              <NavLink to="/configuracoes">Configurações</NavLink>
            )}
            <NavLink to="/ajuda">Ajuda</NavLink>
          </nav>
        </div>
        <div className="sidebar-footer">
          <div className="user-info">
            <strong>{user?.username}</strong>
            <span className="badge">{roleLabel(user?.role)}</span>
            {user?.estabelecimento && (
              <span className="estab">{user.estabelecimento}</span>
            )}
          </div>
          <button className="btn-ghost btn-ghost--sidebar" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
