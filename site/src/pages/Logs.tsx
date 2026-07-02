import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import NotaDetalheModal from "../components/notas/NotaDetalheModal";
import { formatDataHora, buildQuery } from "../lib/format";
import type { NotaStatus } from "../types";
import { NOTA_STATUS_OPTIONS } from "../types";

export default function Logs() {
  const [logs, setLogs] = useState<NotaStatus[]>([]);
  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);
  const [estabelecimento, setEstabelecimento] = useState("");
  const [status, setStatus] = useState("");
  const [somenteErro, setSomenteErro] = useState(true);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [notaSelecionada, setNotaSelecionada] = useState<NotaStatus | null>(null);
  const [expandidoId, setExpandidoId] = useState<number | null>(null);

  const carregarLogs = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const query = buildQuery({
        estabelecimento: estabelecimento || undefined,
        status: status || undefined,
        somente_erro: somenteErro ? "true" : "false",
        limit: "100",
      });
      const lista = await api<NotaStatus[]>(`/admin/logs${query}`);
      setLogs(lista);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao carregar logs");
    } finally {
      setCarregando(false);
    }
  }, [estabelecimento, somenteErro, status]);

  useEffect(() => {
    api<string[]>("/estabelecimentos")
      .then(setEstabelecimentos)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    void carregarLogs();
  }, [carregarLogs]);

  const toggleExpandir = (id: number) => {
    setExpandidoId((atual) => (atual === id ? null : id));
  };

  return (
    <div className="page">
      <h1>Logs técnicos</h1>
      <p className="page-subtitle">
        Histórico de processamento e erros detalhados — acesso restrito a administradores.
      </p>

      <div className="card">
        <div className="logs-filters">
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

          <label className="logs-checkbox">
            <input
              type="checkbox"
              checked={somenteErro}
              onChange={(e) => setSomenteErro(e.target.checked)}
            />
            Somente com erro
          </label>

          <button className="btn-primary" type="button" onClick={() => void carregarLogs()}>
            {carregando ? "Atualizando..." : "Atualizar"}
          </button>
        </div>

        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Eventos recentes</h2>
            <p className="card-subtitle">
              {logs.length} registro(s) — clique na linha para detalhes da nota ou no erro para
              expandir
            </p>
          </div>
        </div>

        <div className="logs-table-wrap">
          <table className="table table-logs">
            <thead>
              <tr>
                <th>Atualizado</th>
                <th>NF</th>
                <th>Seq</th>
                <th>Estab.</th>
                <th>Status</th>
                <th>Tent.</th>
                <th>Erro / detalhe</th>
              </tr>
            </thead>
            <tbody>
              {carregando ? (
                <tr>
                  <td colSpan={7} className="empty">
                    Carregando...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty">
                    Nenhum registro encontrado.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const expandido = expandidoId === log.id;
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
                        <td>{log.tentativas}</td>
                        <td
                          className="log-erro-cell"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpandir(log.id);
                          }}
                          title="Clique para expandir/recolher"
                        >
                          {log.erro ?? "—"}
                        </td>
                      </tr>
                      {expandido && log.erro ? (
                        <tr className="log-erro-expand-row">
                          <td colSpan={7}>
                            <pre className="log-erro-pre">{log.erro}</pre>
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
      </div>

      <NotaDetalheModal nota={notaSelecionada} onClose={() => setNotaSelecionada(null)} />
    </div>
  );
}
