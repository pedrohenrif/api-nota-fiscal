import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

interface EstabelecimentoConfig {
  estabelecimento: string;
  scheduler_enabled: boolean;
  report_enabled: boolean;
  updated_at?: string | null;
}

interface RelatorioResult {
  estabelecimento: string;
  enviado: boolean;
  motivo?: string;
  totais?: Record<string, number>;
  destinatarios?: string[];
}

interface ReportSettings {
  report_interval_minutes: number;
  report_interval_options: number[];
  scheduler_enabled?: boolean;
  mensagem?: string;
}

export default function Configuracoes() {
  const [configs, setConfigs] = useState<EstabelecimentoConfig[]>([]);
  const [reportSettings, setReportSettings] = useState<ReportSettings | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [salvando, setSalvando] = useState<string | null>(null);
  const [enviando, setEnviando] = useState<string | null>(null);
  const [salvandoIntervalo, setSalvandoIntervalo] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const [lista, settings] = await Promise.all([
        api<EstabelecimentoConfig[]>("/admin/estabelecimentos/config"),
        api<ReportSettings>("/admin/relatorios/config"),
      ]);
      setConfigs(lista);
      setReportSettings(settings);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao carregar configuracoes");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const atualizarFlag = async (
    estabelecimento: string,
    patch: Partial<Pick<EstabelecimentoConfig, "scheduler_enabled" | "report_enabled">>
  ) => {
    setSalvando(estabelecimento);
    setErro(null);
    setMensagem(null);
    try {
      const updated = await api<EstabelecimentoConfig>(
        `/admin/estabelecimentos/${encodeURIComponent(estabelecimento)}/config`,
        { method: "PATCH", body: patch }
      );
      setConfigs((atual) =>
        atual.map((item) =>
          item.estabelecimento === estabelecimento ? { ...item, ...updated } : item
        )
      );
      setMensagem(`Configuracao de ${estabelecimento} atualizada.`);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao salvar");
      await carregar();
    } finally {
      setSalvando(null);
    }
  };

  const salvarIntervalo = async (minutes: number) => {
    setSalvandoIntervalo(true);
    setErro(null);
    setMensagem(null);
    try {
      const updated = await api<ReportSettings>("/admin/relatorios/config", {
        method: "PATCH",
        body: { report_interval_minutes: minutes },
      });
      setReportSettings(updated);
      setMensagem(
        updated.mensagem ||
          `Intervalo do e-mail atualizado para ${minutes} minutos.`
      );
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao salvar intervalo");
    } finally {
      setSalvandoIntervalo(false);
    }
  };

  const enviarRelatorio = async (estabelecimento: string) => {
    setEnviando(estabelecimento);
    setErro(null);
    setMensagem(null);
    try {
      const result = await api<RelatorioResult>("/admin/relatorios/enviar", {
        method: "POST",
        body: { estabelecimento },
      });
      if (result.enviado) {
        setMensagem(
          `Relatorio de ${estabelecimento} enviado para ${(result.destinatarios || []).join(", ")}.`
        );
      } else {
        setMensagem(
          `Relatorio de ${estabelecimento}: ${result.motivo || "nenhuma ocorrencia"}.`
        );
      }
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao enviar relatorio");
    } finally {
      setEnviando(null);
    }
  };

  const intervalo = reportSettings?.report_interval_minutes ?? 6;
  const opcoes = reportSettings?.report_interval_options?.length
    ? reportSettings.report_interval_options
    : [6, 30];

  return (
    <div className="page">
      <h1>Configuracoes</h1>
      <p className="page-subtitle">
        Controle o ciclo automatico do extractor (6 min) e o envio de relatorios por e-mail
        ({intervalo} min) por estabelecimento. A emissao manual pelo painel continua disponivel
        mesmo com o scheduler desligado. E-mail automatico dispara apenas com pendencias/erros
        (de-para, lote, retorno PR); notas ja emitidas nao disparam o ciclo sozinhas.
      </p>

      {mensagem ? <div className="alert-success">{mensagem}</div> : null}
      {erro ? <div className="alert-error">{erro}</div> : null}

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <div>
            <h2>Intervalo do e-mail</h2>
            <p className="card-subtitle">
              Global para todas as unidades com relatorio ligado
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label className="toggle-label" style={{ gap: 8 }}>
            Frequencia
            <select
              value={intervalo}
              disabled={salvandoIntervalo || carregando}
              onChange={(e) => void salvarIntervalo(Number(e.target.value))}
            >
              {opcoes.map((opt) => (
                <option key={opt} value={opt}>
                  A cada {opt} minutos
                </option>
              ))}
            </select>
          </label>
          {salvandoIntervalo ? <span className="text-muted">Salvando...</span> : null}
        </div>
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Estabelecimentos</h2>
            <p className="card-subtitle">
              Scheduler = extracao automatica · Relatorio = e-mail automatico
            </p>
          </div>
          <button className="btn-ghost" type="button" onClick={() => void carregar()}>
            Atualizar
          </button>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Estabelecimento</th>
              <th>Scheduler (6 min)</th>
              <th>Relatorio e-mail ({intervalo} min)</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {carregando ? (
              <tr>
                <td colSpan={4} className="empty">
                  Carregando...
                </td>
              </tr>
            ) : (
              configs.map((cfg) => (
                <tr key={cfg.estabelecimento}>
                  <td>
                    <strong>{cfg.estabelecimento}</strong>
                  </td>
                  <td>
                    <label className="toggle-label">
                      <input
                        type="checkbox"
                        checked={cfg.scheduler_enabled}
                        disabled={salvando === cfg.estabelecimento}
                        onChange={(e) =>
                          void atualizarFlag(cfg.estabelecimento, {
                            scheduler_enabled: e.target.checked,
                          })
                        }
                      />
                      {cfg.scheduler_enabled ? "Ligado" : "Desligado"}
                    </label>
                  </td>
                  <td>
                    <label className="toggle-label">
                      <input
                        type="checkbox"
                        checked={cfg.report_enabled}
                        disabled={salvando === cfg.estabelecimento}
                        onChange={(e) =>
                          void atualizarFlag(cfg.estabelecimento, {
                            report_enabled: e.target.checked,
                          })
                        }
                      />
                      {cfg.report_enabled ? "Ligado" : "Desligado"}
                    </label>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn-table"
                      disabled={enviando === cfg.estabelecimento}
                      onClick={() => void enviarRelatorio(cfg.estabelecimento)}
                    >
                      {enviando === cfg.estabelecimento
                        ? "Enviando..."
                        : "Enviar relatorio agora"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
