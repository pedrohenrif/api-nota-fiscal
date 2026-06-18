import { NavLink, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth";
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
        <BrandLogo />
        <nav>
          <NavLink to="/" end>
            Emitir Nota
          </NavLink>
          {user?.role === "adm" && <NavLink to="/usuarios">Usuários</NavLink>}
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">
            <strong>{user?.username}</strong>
            <span className="badge">{user?.role === "adm" ? "Admin" : "Usuário"}</span>
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
