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

export default function Configuracoes() {
  const [configs, setConfigs] = useState<EstabelecimentoConfig[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [salvando, setSalvando] = useState<string | null>(null);
  const [enviando, setEnviando] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const lista = await api<EstabelecimentoConfig[]>("/admin/estabelecimentos/config");
      setConfigs(lista);
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

  return (
    <div className="page">
      <h1>Configuracoes</h1>
      <p className="page-subtitle">
        Controle o ciclo automatico do extractor (6 min) e o envio de relatorios por e-mail (30 min)
        por estabelecimento. A emissao manual pelo painel continua disponivel mesmo com o
        scheduler desligado.
      </p>

      {mensagem ? <div className="alert-success">{mensagem}</div> : null}
      {erro ? <div className="alert-error">{erro}</div> : null}

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
              <th>Relatorio e-mail (30 min)</th>
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
