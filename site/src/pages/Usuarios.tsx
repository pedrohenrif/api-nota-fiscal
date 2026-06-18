import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { Role, Usuario } from "../types";

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);

  const [username, setUsername] = useState("");
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
        if (lista.length > 0) {
          setEstabelecimento(lista[0]);
        }
      })
      .catch(() => undefined);
  }, [carregarUsuarios]);

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
          role,
          estabelecimento: role === "usuario" ? estabelecimento : null,
        },
      });
      setMensagem(`Usuário "${username}" criado com sucesso.`);
      setUsername("");
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

      <div className="card">
        <h2>Novo usuário</h2>
        <form className="form-grid" onSubmit={criar}>
          <label>
            Usuário
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            Senha
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
              <option value="usuario">Usuário</option>
              <option value="adm">Administrador</option>
            </select>
          </label>
          {role === "usuario" && (
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
        <h2>Usuários cadastrados</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Usuário</th>
              <th>Papel</th>
              <th>Estabelecimento</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.role === "adm" ? "Administrador" : "Usuário"}</td>
                <td>{u.estabelecimento ?? "Todos"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
