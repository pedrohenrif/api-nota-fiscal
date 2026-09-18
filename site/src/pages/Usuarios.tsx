import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { creatableRoles, isGlobalAdmin, roleLabel } from "../lib/roles";
import type { Role, Usuario } from "../types";

export default function Usuarios() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);
  const [carregando, setCarregando] = useState(true);

  const allowedRoles = useMemo(() => creatableRoles(user?.role), [user?.role]);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("usuario");
  const [estabelecimento, setEstabelecimento] = useState("");

  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const carregarUsuarios = useCallback(async () => {
    setCarregando(true);
    try {
      const lista = await api<Usuario[]>("/usuarios");
      setUsuarios(lista);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao carregar usuários");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregarUsuarios();
    api<string[]>("/estabelecimentos")
      .then((lista) => {
        setEstabelecimentos(lista);
        if (lista.length > 0) setEstabelecimento(lista[0]);
      })
      .catch(() => undefined);
  }, [carregarUsuarios]);

  useEffect(() => {
    if (allowedRoles.length && !allowedRoles.includes(role)) {
      setRole(allowedRoles[0]);
    }
  }, [allowedRoles, role]);

  const needsEstab = role === "usuario" || role === "adm_local";

  const criar = async (event: FormEvent) => {
    event.preventDefault();
    setErro(null);
    setMensagem(null);
    setSalvando(true);
    try {
      await api<Usuario>("/usuarios", {
        method: "POST",
        body: {
          username,
          password,
          email: email.trim() || null,
          role,
          estabelecimento: needsEstab
            ? isGlobalAdmin(user?.role)
              ? estabelecimento
              : user?.estabelecimento
            : null,
        },
      });
      setMensagem(`Usuário "${username}" criado com sucesso.`);
      setUsername("");
      setEmail("");
      setPassword("");
      setRole(allowedRoles.includes("usuario") ? "usuario" : allowedRoles[0]);
      await carregarUsuarios();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao criar usuário");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="page">
      <h1>Usuários</h1>
      <p className="page-lead">
        {isGlobalAdmin(user?.role)
          ? "Cadastro global de usuários (incluindo adm local e dev). Informe o e-mail para permitir recuperação de senha."
          : `Cadastro de usuários da unidade ${user?.estabelecimento ?? ""}. Informe o e-mail para recuperação de senha.`}
      </p>

      <div className="card">
        <div className="card-header">
          <div>
            <h2>Novo usuário</h2>
            <p className="card-subtitle">Preencha os dados e clique em criar</p>
          </div>
        </div>

        <form className="usuarios-form" onSubmit={criar}>
          <div className="filters-grid">
            <label className="filter-field">
              <span className="filter-label">Usuário</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="login"
                required
                autoComplete="off"
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">E-mail</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="opcional, recomendado"
                autoComplete="off"
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">Senha inicial</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">Papel</span>
              <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                {allowedRoles.map((r) => (
                  <option key={r} value={r}>
                    {roleLabel(r)}
                  </option>
                ))}
              </select>
            </label>
            {needsEstab && isGlobalAdmin(user?.role) ? (
              <label className="filter-field">
                <span className="filter-label">Estabelecimento</span>
                <select
                  value={estabelecimento}
                  onChange={(e) => setEstabelecimento(e.target.value)}
                >
                  {estabelecimentos.map((est) => (
                    <option key={est} value={est}>
                      {est}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {needsEstab && !isGlobalAdmin(user?.role) ? (
              <div className="filter-field">
                <span className="filter-label">Estabelecimento</span>
                <div className="estab-fixed" style={{ paddingTop: 8 }}>
                  <strong>{user?.estabelecimento}</strong>
                </div>
              </div>
            ) : null}
            {!needsEstab ? (
              <div className="filter-field">
                <span className="filter-label">Estabelecimento</span>
                <div className="estab-fixed" style={{ paddingTop: 8 }}>
                  <strong>Todos</strong> (papel global)
                </div>
              </div>
            ) : null}
          </div>

          <div className="filters-actions">
            <button className="btn-primary" type="submit" disabled={salvando}>
              {salvando ? "Salvando..." : "Criar usuário"}
            </button>
          </div>
        </form>

        {mensagem ? <div className="alert-success">{mensagem}</div> : null}
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Cadastrados</h2>
            <p className="card-subtitle">{usuarios.length} usuário(s)</p>
          </div>
        </div>

        <div className="table-scroll">
          <table className="table table-usuarios">
            <thead>
              <tr>
                <th>Usuário</th>
                <th>E-mail</th>
                <th>Papel</th>
                <th>Estabelecimento</th>
              </tr>
            </thead>
            <tbody>
              {carregando ? (
                <tr>
                  <td colSpan={4} className="empty">
                    Carregando...
                  </td>
                </tr>
              ) : usuarios.length === 0 ? (
                <tr>
                  <td colSpan={4} className="empty">
                    Nenhum usuário cadastrado.
                  </td>
                </tr>
              ) : (
                usuarios.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.username}</strong>
                    </td>
                    <td className="cell-email">{u.email || "—"}</td>
                    <td>
                      <span className={`role-pill role-pill--${u.role}`}>{roleLabel(u.role)}</span>
                    </td>
                    <td>{u.estabelecimento || "Todos"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
