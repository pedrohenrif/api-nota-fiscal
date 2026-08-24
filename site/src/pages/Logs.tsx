import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import NotaDetalheModal from "../components/notas/NotaDetalheModal";
import Pagination from "../components/Pagination";
import { formatDataHora, buildQuery } from "../lib/format";
import { formatRetornoPr } from "../lib/notas";
import type { NotaStatus, NotaStatusPage } from "../types";
import { ERRO_TIPO_LABELS, ERRO_TIPO_OPTIONS, NOTA_STATUS_OPTIONS } from "../types";

const PAGE_SIZE = 50;

export default function Logs() {
  const [logs, setLogs] = useState<NotaStatus[]>([]);
  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);
  const [estabelecimento, setEstabelecimento] = useState("");
  const [status, setStatus] = useState("");
  const [erroTipo, setErroTipo] = useState("");
  const [somenteErro, setSomenteErro] = useState(true);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [notaSelecionada, setNotaSelecionada] = useState<NotaStatus | null>(null);
  const [expandidoId, setExpandidoId] = useState<number | null>(null);
  const [jaPesquisou, setJaPesquisou] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const carregarLogs = useCallback(
    async (pageOverride?: number) => {
      const pageToLoad = pageOverride ?? page;
      setCarregando(true);
      setErro(null);
      try {
        const query = buildQuery({
          estabelecimento: estabelecimento || undefined,
          status: status || undefined,
          erro_tipo: erroTipo || undefined,
          somente_erro: somenteErro ? "true" : "false",
          page: String(pageToLoad),
          page_size: String(PAGE_SIZE),
        });
        const result = await api<NotaStatusPage>(`/admin/logs${query}`);
        setLogs(result.items);
        setTotal(result.total);
        setPage(result.page);
        setTotalPages(result.total_pages);
        setJaPesquisou(true);
      } catch (err) {
        setErro(err instanceof Error ? err.message : "Erro ao carregar logs");
      } finally {
        setCarregando(false);
      }
    },
    [estabelecimento, erroTipo, page, somenteErro, status]
  );

  useEffect(() => {
    api<string[]>("/estabelecimentos")
      .then(setEstabelecimentos)
      .catch(() => undefined);
  }, []);

  const toggleExpandir = (id: number) => {
    setExpandidoId((atual) => (atual === id ? null : id));
  };

  return (
    <div className="page">
      <h1>Logs de processamento</h1>

      <div className="card">
        <div className="row logs-filters">
          <label>
            Estabelecimento
            <select value={estabelecimento} onChange={(e) => setEstabelecimento(e.target.value)}>
              <option value="">Todos</option>
              {estabelecimentos.map((est) => (
                <option key={est} value={est}>
                  {est}
                </option>
              ))}
            </select>
          </label>

          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {NOTA_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Tipo de erro
            <select value={erroTipo} onChange={(e) => setErroTipo(e.target.value)}>
              {ERRO_TIPO_OPTIONS.map((opt) => (
                <option key={opt.value || "all-erro"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="logs-checkbox">
            <input
              type="checkbox"
              checked={somenteErro}
              onChange={(e) => setSomenteErro(e.target.checked)}
            />
            Somente com erro
          </label>

          <button
            className="btn-primary"
            type="button"
            onClick={() => {
              setPage(1);
              void carregarLogs(1);
            }}
          >
            {carregando ? "Atualizando..." : "Pesquisar"}
          </button>
        </div>
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Atualizado</th>
                <th>NF</th>
                <th>Seq.</th>
                <th>Estabelecimento</th>
                <th>Status</th>
                <th>Tipo erro</th>
                <th>Tent.</th>
                <th>Retorno PR</th>
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
                    Defina os filtros e clique em Pesquisar.
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty">
                    Nenhum registro encontrado.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const expandido = expandidoId === log.id;
                  const retorno = formatRetornoPr(log);
                  const detalhe = retorno.kind === "error" ? log.erro : retorno.text;
                  return (
                    <Fragment key={log.id}>
                      <tr
                        className="table-row-clickable"
                        onClick={() => setNotaSelecionada(log)}
                        title="Clique para abrir detalhes da nota"
                      >
                        <td>{formatDataHora(log.updated_at ?? log.created_at)}</td>
                        <td>{log.nf}</td>
                        <td>{log.nr_sequencia ?? "—"}</td>
                        <td>{log.estabelecimento}</td>
                        <td>
                          <span className={`status status-${log.status}`}>{log.status}</span>
                        </td>
                        <td>
                          {log.erro_tipo ? (
                            <span className={`erro-tipo erro-tipo-${log.erro_tipo}`}>
                              {ERRO_TIPO_LABELS[log.erro_tipo] ?? log.erro_tipo}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>{log.tentativas}</td>
                        <td
                          className={
                            retorno.kind === "success"
                              ? "pr-success-cell log-erro-cell"
                              : "log-erro-cell"
                          }
                          onClick={(e) => {
                            if (retorno.kind !== "error") return;
                            e.stopPropagation();
                            toggleExpandir(log.id);
                          }}
                          title={
                            retorno.kind === "error"
                              ? "Clique para expandir/recolher"
                              : retorno.title
                          }
                        >
                          {retorno.text}
                        </td>
                      </tr>
                      {expandido && detalhe && retorno.kind === "error" ? (
                        <tr className="log-erro-expand-row">
                          <td colSpan={8}>
                            <pre className="log-erro-pre">{detalhe}</pre>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={PAGE_SIZE}
          disabled={carregando || !jaPesquisou}
          onChange={(p) => void carregarLogs(p)}
        />
      </div>

      <NotaDetalheModal
        nota={notaSelecionada}
        onClose={() => setNotaSelecionada(null)}
        onAtualizado={() => {
          if (jaPesquisou) void carregarLogs(page);
        }}
      />
    </div>
  );
}
