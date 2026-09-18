import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { creatableRoles, isGlobalAdmin, roleLabel } from "../lib/roles";
import type { Role, Usuario } from "../types";

export default function Usuarios() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);

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
    try {
      const lista = await api<Usuario[]>("/usuarios");
      setUsuarios(lista);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao carregar usuários");
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
      setRole("usuario");
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
          ? "Cadastro global de usuários (incluindo adm local e dev)."
          : `Cadastro de usuários da unidade ${user?.estabelecimento ?? ""}.`}
      </p>

      <div className="card">
        <h2>Novo usuário</h2>
        <form className="form-grid" onSubmit={criar}>
          <label>
            Usuário
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            E-mail (para recuperar senha)
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="opcional, mas recomendado"
            />
          </label>
          <label>
            Senha inicial
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <label>
            Papel
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {allowedRoles.map((r) => (
                <option key={r} value={r}>
                  {roleLabel(r)}
                </option>
              ))}
            </select>
          </label>
          {needsEstab && isGlobalAdmin(user?.role) && (
            <label>
              Estabelecimento
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
          )}
          {needsEstab && !isGlobalAdmin(user?.role) && (
            <div className="estab-fixed">
              Estabelecimento: <strong>{user?.estabelecimento}</strong>
            </div>
          )}

          <div className="form-actions">
            <button className="btn-primary" type="submit" disabled={salvando}>
              {salvando ? "Salvando..." : "Criar usuário"}
            </button>
          </div>
        </form>

        {mensagem && <div className="alert-success">{mensagem}</div>}
        {erro && <div className="alert-error">{erro}</div>}
      </div>

      <div className="card">
        <h2>Cadastrados</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Usuário</th>
                <th>E-mail</th>
                <th>Papel</th>
                <th>Estabelecimento</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>{u.email || "—"}</td>
                  <td>{roleLabel(u.role)}</td>
                  <td>{u.estabelecimento || "Todos"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
