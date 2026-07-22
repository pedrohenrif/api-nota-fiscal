import { useCallback, useEffect, useMemo, useState } from "react";
import { api, getToken } from "../api";
import { useAuth } from "../auth";
import { buildQuery, formatDataHora } from "../lib/format";
import type { NotaStatus } from "../types";
import { ERRO_TIPO_LABELS, ERRO_TIPO_OPTIONS, NOTA_STATUS_OPTIONS } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
  /\/$/,
  ""
) || "http://localhost:8003";

interface DashboardKpis {
  total: number;
  sent: number;
  retry_pending: number;
  dead_letter: number;
  pending: number;
  com_erro: number;
  taxa_sucesso_pct: number;
  taxa_erro_pct: number;
}

interface DashboardResumo {
  kpis: DashboardKpis;
  por_status: { status: string; qtd: number }[];
  por_erro_tipo: { erro_tipo: string; qtd: number }[];
  por_estabelecimento: {
    estabelecimento: string;
    total: number;
    sent: number;
    retry_pending: number;
    dead_letter: number;
    pending: number;
  }[];
  serie_diaria: { dia: string | null; sent: number; erros: number; total: number }[];
  recentes_com_erro: NotaStatus[];
}

function BarRow({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  const pct = max > 0 ? Math.max((value / max) * 100, value > 0 ? 4 : 0) : 0;
  return (
    <div className="dash-bar-row">
      <div className="dash-bar-label">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="dash-bar-track">
        <div className={`dash-bar-fill dash-bar-fill--${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const isAdmin = user?.role === "adm";

  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);
  const [estabelecimento, setEstabelecimento] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [usarDataNf, setUsarDataNf] = useState(false);
  const [statusExport, setStatusExport] = useState("");
  const [erroTipoExport, setErroTipoExport] = useState("");
  const [resumo, setResumo] = useState<DashboardResumo | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api<string[]>("/estabelecimentos")
      .then((lista) => {
        setEstabelecimentos(lista);
        if (!isAdmin && lista[0]) setEstabelecimento(lista[0]);
      })
      .catch(() => undefined);
  }, [isAdmin]);

  const queryParams = useMemo(
    () => ({
      ...(isAdmin && estabelecimento ? { estabelecimento } : {}),
      data_inicio: dataInicio || undefined,
      data_fim: dataFim || undefined,
      usar_data_nf: usarDataNf ? "true" : "false",
    }),
    [dataFim, dataInicio, estabelecimento, isAdmin, usarDataNf]
  );

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await api<DashboardResumo>(`/dashboard/resumo${buildQuery(queryParams)}`);
      setResumo(data);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao carregar dashboard");
    } finally {
      setCarregando(false);
    }
  }, [queryParams]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const exportar = async () => {
    setExportando(true);
    setErro(null);
    try {
      const query = buildQuery({
        ...queryParams,
        status: statusExport || undefined,
        erro_tipo: erroTipoExport || undefined,
      });
      const token = getToken();
      const response = await fetch(`${API_BASE_URL}/dashboard/export${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        let detail = `Erro ${response.status}`;
        try {
          const body = await response.json();
          if (typeof body?.detail === "string") detail = body.detail;
        } catch {
          // ignore
        }
        throw new Error(detail);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      a.href = url;
      a.download = `relatorio_notas_${stamp}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao exportar");
    } finally {
      setExportando(false);
    }
  };

  const kpis = resumo?.kpis;
  const maxStatus = Math.max(1, ...(resumo?.por_status.map((i) => i.qtd) ?? [1]));
  const maxErro = Math.max(1, ...(resumo?.por_erro_tipo.map((i) => i.qtd) ?? [1]));
  const maxSerie = Math.max(
    1,
    ...(resumo?.serie_diaria.flatMap((d) => [d.sent, d.erros]) ?? [1])
  );

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p className="page-lead">
        Visão da integração de notas (sucessos, erros e volume). Use o período e exporte o relatório
        completo para controle.
      </p>

      <div className="card">
        <div className="filters-grid">
          {isAdmin ? (
            <label className="filter-field">
              <span className="filter-label">Estabelecimento</span>
              <select
                value={estabelecimento}
                onChange={(e) => setEstabelecimento(e.target.value)}
              >
                <option value="">Todos</option>
                {estabelecimentos.map((est) => (
                  <option key={est} value={est}>
                    {est}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <div className="estab-fixed">
              Estabelecimento: <strong>{user?.estabelecimento ?? "—"}</strong>
            </div>
          )}
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
          <label className="filter-field logs-checkbox" style={{ alignSelf: "end" }}>
            <input
              type="checkbox"
              checked={usarDataNf}
              onChange={(e) => setUsarDataNf(e.target.checked)}
            />
            Filtrar pela Data NF (senão usa data de atualização)
          </label>
        </div>
        <div className="filters-actions">
          <button type="button" className="btn-primary" onClick={() => void carregar()}>
            {carregando ? "Atualizando..." : "Atualizar dashboard"}
          </button>
        </div>
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      {kpis ? (
        <div className="dash-kpi-grid">
          <div className="dash-kpi">
            <span>Total no período</span>
            <strong>{kpis.total}</strong>
          </div>
          <div className="dash-kpi dash-kpi--ok">
            <span>Integradas (sent)</span>
            <strong>{kpis.sent}</strong>
            <em>{kpis.taxa_sucesso_pct}% sucesso</em>
          </div>
          <div className="dash-kpi dash-kpi--warn">
            <span>Retry pendente</span>
            <strong>{kpis.retry_pending}</strong>
          </div>
          <div className="dash-kpi dash-kpi--danger">
            <span>Dead letter</span>
            <strong>{kpis.dead_letter}</strong>
            <em>{kpis.taxa_erro_pct}% com erro</em>
          </div>
          <div className="dash-kpi">
            <span>Pending</span>
            <strong>{kpis.pending}</strong>
          </div>
          <div className="dash-kpi dash-kpi--danger">
            <span>Com erro (retry + DLQ)</span>
            <strong>{kpis.com_erro}</strong>
          </div>
        </div>
      ) : null}

      <div className="dash-panels">
        <section className="card">
          <h2>Por status</h2>
          {resumo?.por_status.length ? (
            resumo.por_status.map((item) => (
              <BarRow
                key={item.status}
                label={item.status}
                value={item.qtd}
                max={maxStatus}
                tone={
                  item.status === "sent"
                    ? "ok"
                    : item.status === "dead_letter"
                      ? "danger"
                      : item.status === "retry_pending"
                        ? "warn"
                        : "muted"
                }
              />
            ))
          ) : (
            <p className="help-text">Sem dados no período.</p>
          )}
        </section>

        <section className="card">
          <h2>Erros por tipo</h2>
          {resumo?.por_erro_tipo.length ? (
            resumo.por_erro_tipo.map((item) => (
              <BarRow
                key={item.erro_tipo}
                label={ERRO_TIPO_LABELS[item.erro_tipo] ?? item.erro_tipo}
                value={item.qtd}
                max={maxErro}
                tone={
                  item.erro_tipo === "sem_depara"
                    ? "danger"
                    : item.erro_tipo === "sem_lote"
                      ? "warn"
                      : "muted"
                }
              />
            ))
          ) : (
            <p className="help-text">Nenhum erro classificado no período.</p>
          )}
        </section>
      </div>

      {isAdmin && resumo ? (
        <section className="card card-table">
          <div className="card-header">
            <div>
              <h2>Por estabelecimento</h2>
              <p className="card-subtitle">Volume e distribuição de status</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Estabelecimento</th>
                  <th>Total</th>
                  <th>Sent</th>
                  <th>Retry</th>
                  <th>Dead letter</th>
                  <th>Pending</th>
                  <th>% sucesso</th>
                </tr>
              </thead>
              <tbody>
                {resumo.por_estabelecimento.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="empty">
                      Sem dados.
                    </td>
                  </tr>
                ) : (
                  resumo.por_estabelecimento.map((row) => {
                    const total = Number(row.total) || 0;
                    const sent = Number(row.sent) || 0;
                    const pct = total ? ((sent / total) * 100).toFixed(1) : "0.0";
                    return (
                      <tr key={row.estabelecimento}>
                        <td>{row.estabelecimento}</td>
                        <td>{total}</td>
                        <td>{sent}</td>
                        <td>{row.retry_pending}</td>
                        <td>{row.dead_letter}</td>
                        <td>{row.pending}</td>
                        <td>{pct}%</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Evolução diária</h2>
            <p className="card-subtitle">Últimos dias com movimento (integradas vs erros)</p>
          </div>
        </div>
        {resumo?.serie_diaria?.length ? (
          <div className="dash-serie">
            {resumo.serie_diaria.map((dia) => (
              <div key={String(dia.dia)} className="dash-serie-col" title={String(dia.dia)}>
                <div className="dash-serie-bars">
                  <div
                    className="dash-serie-bar dash-serie-bar--ok"
                    style={{ height: `${(dia.sent / maxSerie) * 100}%` }}
                  />
                  <div
                    className="dash-serie-bar dash-serie-bar--danger"
                    style={{ height: `${(dia.erros / maxSerie) * 100}%` }}
                  />
                </div>
                <span>
                  {dia.dia
                    ? new Date(`${dia.dia}T12:00:00`).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                      })
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="help-text">Sem série diária no período.</p>
        )}
        <div className="dash-serie-legend">
          <span>
            <i className="dash-dot dash-dot--ok" /> Integradas
          </span>
          <span>
            <i className="dash-dot dash-dot--danger" /> Erros
          </span>
        </div>
      </section>

      <section className="card card-table">
        <div className="card-header">
          <div>
            <h2>Erros recentes</h2>
            <p className="card-subtitle">Últimas notas em retry ou dead letter</p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Atualizado</th>
                <th>NF</th>
                <th>Seq.</th>
                <th>Estab.</th>
                <th>Status</th>
                <th>Tipo erro</th>
                <th>Retorno / erro</th>
              </tr>
            </thead>
            <tbody>
              {!resumo?.recentes_com_erro?.length ? (
                <tr>
                  <td colSpan={7} className="empty">
                    Nenhum erro recente no filtro.
                  </td>
                </tr>
              ) : (
                resumo.recentes_com_erro.map((nota) => (
                  <tr key={nota.id}>
                    <td>{formatDataHora(nota.updated_at)}</td>
                    <td>{nota.nf}</td>
                    <td>{nota.nr_sequencia ?? "—"}</td>
                    <td>{nota.estabelecimento}</td>
                    <td>
                      <span className={`status status-${nota.status}`}>{nota.status}</span>
                    </td>
                    <td>
                      {nota.erro_tipo
                        ? (ERRO_TIPO_LABELS[nota.erro_tipo] ?? nota.erro_tipo)
                        : "—"}
                    </td>
                    <td className="erro-cell" title={nota.erro ?? nota.pr_mensagem ?? undefined}>
                      {nota.erro || nota.pr_mensagem || "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Exportar relatório</h2>
            <p className="card-subtitle">
              CSV (Excel) com todos os campos da nota no middleware — até 50.000 linhas
            </p>
          </div>
        </div>
        <div className="filters-grid">
          <label className="filter-field">
            <span className="filter-label">Status (opcional)</span>
            <select value={statusExport} onChange={(e) => setStatusExport(e.target.value)}>
              {NOTA_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span className="filter-label">Tipo de erro (opcional)</span>
            <select value={erroTipoExport} onChange={(e) => setErroTipoExport(e.target.value)}>
              {ERRO_TIPO_OPTIONS.map((opt) => (
                <option key={opt.value || "all-erro"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="filters-actions">
          <button
            type="button"
            className="btn-primary"
            disabled={exportando}
            onClick={() => void exportar()}
          >
            {exportando ? "Gerando..." : "Exportar CSV"}
          </button>
        </div>
        <p className="help-text">
          Colunas: id, estabelecimento, nf, nr_sequencia, fornecedor, data_nf, status, tentativas,
          erro_tipo, erro, pr_id, pr_mensagem, created_at, updated_at. Separador `;` com BOM UTF-8
          para abrir direto no Excel.
        </p>
      </section>
    </div>
  );
}
