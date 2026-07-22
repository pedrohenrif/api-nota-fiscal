import { useCallback, useState } from "react";
import { api } from "../api";
import { buildQuery, formatDataHora } from "../lib/format";
import type { AccessAuditLog, AccessAuditPage } from "../types";
import Pagination from "../components/Pagination";

export default function Acesso() {
  const [items, setItems] = useState<AccessAuditLog[]>([]);
  const [username, setUsername] = useState("");
  const [ip, setIp] = useState("");
  const [action, setAction] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [jaPesquisou, setJaPesquisou] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 50;

  const carregar = useCallback(
    async (pageOverride?: number) => {
      const pageToLoad = pageOverride ?? page;
      setCarregando(true);
      setErro(null);
      try {
        const query = buildQuery({
          username: username || undefined,
          ip: ip || undefined,
          action: action || undefined,
          limit: String(pageSize),
          offset: String((pageToLoad - 1) * pageSize),
        });
        const result = await api<AccessAuditPage>(`/admin/acesso${query}`);
        setItems(result.items);
        setTotal(result.total);
        setPage(pageToLoad);
        setJaPesquisou(true);
      } catch (err) {
        setErro(err instanceof Error ? err.message : "Erro ao carregar acessos");
      } finally {
        setCarregando(false);
      }
    },
    [action, ip, page, username]
  );

  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 0;

  return (
    <div className="page">
      <h1>Acessos e auditoria</h1>

      <div className="card">
        <p className="help-text">
          Registro de IP, usuário e ações no painel (login, listagens, emissão, etc.).
        </p>
        <div className="row">
          <label>
            Usuário
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Opcional"
            />
          </label>
          <label>
            IP
            <input value={ip} onChange={(e) => setIp(e.target.value)} placeholder="Opcional" />
          </label>
          <label>
            Ação
            <input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="Ex: login, emitir_pendentes"
            />
          </label>
          <button
            className="btn-primary"
            type="button"
            onClick={() => {
              setPage(1);
              void carregar(1);
            }}
          >
            {carregando ? "Carregando..." : "Pesquisar"}
          </button>
        </div>
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Histórico de acesso</h2>
            <p className="card-subtitle">Ordenado do mais recente para o mais antigo</p>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data/Hora</th>
                <th>Usuário</th>
                <th>IP</th>
                <th>Ação</th>
                <th>Método</th>
                <th>Path</th>
                <th>Status</th>
                <th>Detalhe</th>
              </tr>
            </thead>
            <tbody>
              {carregando ? (
                <tr>
                  <td colSpan={8} className="empty">
                    Carregando...
                  </td>
                </tr>
              ) : !jaPesquisou ? (
                <tr>
                  <td colSpan={8} className="empty">
                    Clique em Pesquisar para carregar o histórico de acessos.
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty">
                    Nenhum registro encontrado.
                  </td>
                </tr>
              ) : (
                items.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDataHora(row.created_at)}</td>
                    <td>
                      {row.username ?? "—"}
                      {row.role ? ` (${row.role})` : ""}
                    </td>
                    <td>{row.ip}</td>
                    <td>{row.action}</td>
                    <td>{row.method}</td>
                    <td className="cell-truncate" title={row.path}>
                      {row.path}
                    </td>
                    <td>{row.status_code}</td>
                    <td className="cell-truncate" title={row.detail ?? undefined}>
                      {row.detail ?? "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={pageSize}
          disabled={carregando}
          onChange={(p) => void carregar(p)}
        />
      </div>
    </div>
  );
}
