import { useCallback, useState } from "react";
import { api } from "../api";
import Pagination from "../components/Pagination";
import { buildQuery, formatDataHora } from "../lib/format";
import type { AccessAuditLog, AccessAuditPage } from "../types";

const ACTION_OPTIONS = [
  { value: "", label: "Todas as ações" },
  { value: "login", label: "login" },
  { value: "login_falha", label: "login_falha" },
  { value: "listar_notas", label: "listar_notas" },
  { value: "emitir_pendentes", label: "emitir_pendentes" },
  { value: "emitir_especifica", label: "emitir_especifica" },
  { value: "reemitir_nota", label: "reemitir_nota" },
  { value: "detalhe_nota", label: "detalhe_nota" },
  { value: "listar_destinatarios", label: "listar_destinatarios" },
  { value: "criar_destinatario", label: "criar_destinatario" },
  { value: "editar_destinatario", label: "editar_destinatario" },
  { value: "excluir_destinatario", label: "excluir_destinatario" },
  { value: "enviar_relatorio", label: "enviar_relatorio" },
  { value: "atualizar_config", label: "atualizar_config" },
];

export default function Acesso() {
  const [items, setItems] = useState<AccessAuditLog[]>([]);
  const [username, setUsername] = useState("");
  const [ip, setIp] = useState("");
  const [action, setAction] = useState("");
  const [role, setRole] = useState("");
  const [estabelecimento, setEstabelecimento] = useState("");
  const [statusCode, setStatusCode] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
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
          role: role || undefined,
          estabelecimento: estabelecimento || undefined,
          status_code: statusCode || undefined,
          data_inicio: dataInicio || undefined,
          data_fim: dataFim || undefined,
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
    [action, dataFim, dataInicio, estabelecimento, ip, page, role, statusCode, username]
  );

  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 0;

  const limpar = () => {
    setUsername("");
    setIp("");
    setAction("");
    setRole("");
    setEstabelecimento("");
    setStatusCode("");
    setDataInicio("");
    setDataFim("");
    setItems([]);
    setTotal(0);
    setPage(1);
    setJaPesquisou(false);
    setErro(null);
  };

  return (
    <div className="page">
      <h1>Acessos e auditoria</h1>
      <p className="page-lead">Visível apenas para administradores.</p>

      <div className="card">
        <p className="help-text">
          Registro de IP, usuário e ações no painel (login, listagens, emissão, destinatários, etc.).
        </p>
        <div className="filters-grid">
          <label className="filter-field">
            <span className="filter-label">Usuário</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Opcional"
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">IP</span>
            <input value={ip} onChange={(e) => setIp(e.target.value)} placeholder="Opcional" />
          </label>
          <label className="filter-field">
            <span className="filter-label">Ação</span>
            <select value={action} onChange={(e) => setAction(e.target.value)}>
              {ACTION_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span className="filter-label">Perfil</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="">Todos</option>
              <option value="adm">Admin</option>
              <option value="usuario">Usuário</option>
            </select>
          </label>
          <label className="filter-field">
            <span className="filter-label">Estabelecimento</span>
            <input
              value={estabelecimento}
              onChange={(e) => setEstabelecimento(e.target.value)}
              placeholder="Ex: Castelo"
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">Status HTTP</span>
            <input
              value={statusCode}
              onChange={(e) => setStatusCode(e.target.value)}
              placeholder="Ex: 200, 401"
              inputMode="numeric"
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">Data — de</span>
            <input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
            />
          </label>
          <label className="filter-field">
            <span className="filter-label">Data — até</span>
            <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} />
          </label>
        </div>
        <div className="filters-actions">
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
          <button className="btn-ghost" type="button" onClick={limpar}>
            Limpar
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

        <div className="table-scroll">
          <table className="table">
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
