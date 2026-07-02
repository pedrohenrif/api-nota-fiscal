import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { formatData, formatDataHora, formatMoeda, formatNumero } from "../../lib/format";
import type { NotaDetalhe, NotaStatus } from "../../types";
import Modal from "../ui/Modal";

interface NotaDetalheModalProps {
  nota: NotaStatus | null;
  onClose: () => void;
}

export default function NotaDetalheModal({ nota, onClose }: NotaDetalheModalProps) {
  const [detalhe, setDetalhe] = useState<NotaDetalhe | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!nota) {
      setDetalhe(null);
      setErro(null);
      return;
    }

    let ativo = true;
    setCarregando(true);
    setErro(null);
    setDetalhe(null);

    void api<NotaDetalhe>(`/notas/${nota.id}/detalhe`)
      .then((result) => {
        if (ativo) setDetalhe(result);
      })
      .catch((err) => {
        if (ativo) setErro(err instanceof Error ? err.message : "Falha ao carregar detalhes");
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });

    return () => {
      ativo = false;
    };
  }, [nota]);

  const preview = detalhe?.preview;
  const somaItens = useMemo(
    () => (preview?.produtos ?? []).reduce((acc, item) => acc + (item.valor ?? 0), 0),
    [preview]
  );

  return (
    <Modal
      open={nota != null}
      title={nota ? `Nota fiscal ${nota.nf}` : "Detalhes da nota"}
      onClose={onClose}
      xl
      footer={
        <button type="button" className="btn-primary" onClick={onClose}>
          Fechar
        </button>
      }
    >
      {carregando ? (
        <p className="detalhe-loading">Carregando detalhes da nota...</p>
      ) : erro ? (
        <div className="alert-error">{erro}</div>
      ) : detalhe ? (
        <>
          <div className="detalhe-status-row">
            <span className={`status status-${detalhe.status}`}>{detalhe.status}</span>
            <span className="detalhe-meta">
              Tentativas: <strong>{detalhe.tentativas}</strong>
            </span>
            {detalhe.erro ? (
              <span className="detalhe-erro-inline" title={detalhe.erro}>
                {detalhe.erro}
              </span>
            ) : null}
          </div>

          <section className="detalhe-section">
            <h3 className="detalhe-section-title">Identificação</h3>
            <div className="consulta-grid detalhe-grid">
              <span>NF</span>
              <strong>{detalhe.nf}</strong>
              <span>NR Sequência</span>
              <strong>{detalhe.nr_sequencia ?? "-"}</strong>
              <span>Estabelecimento</span>
              <strong>{detalhe.estabelecimento}</strong>
              <span>Fornecedor (CNPJ)</span>
              <strong>{detalhe.fornecedor ?? preview?.fornecedor?.cnpj ?? "-"}</strong>
              <span>Data NF</span>
              <strong>{formatData(preview?.dataNF ?? detalhe.data_nf)}</strong>
              <span>Operação Tasy</span>
              <strong>{detalhe.cd_operacao_nf ?? "-"}</strong>
              <span>Operações liberadas</span>
              <strong>{detalhe.operacoes_liberadas.join(", ") || "-"}</strong>
            </div>
          </section>

          {preview ? (
            <>
              <section className="detalhe-section">
                <h3 className="detalhe-section-title">Cabeçalho</h3>
                <div className="consulta-grid detalhe-grid">
                  <span>Série</span>
                  <strong>{preview.serie || "-"}</strong>
                  <span>Operador</span>
                  <strong>{preview.operador ?? "INTEGRACAO"}</strong>
                  <span>Doação</span>
                  <strong>{preview.doacao ? "Sim" : "Não"}</strong>
                  <span>Recebimento</span>
                  <strong>{formatData(preview.dataRecebimento)}</strong>
                  <span>Vencimento</span>
                  <strong>{formatData(preview.vencimento)}</strong>
                  <span>Desconto</span>
                  <strong>{formatMoeda(preview.desconto)}</strong>
                  <span>IPI</span>
                  <strong>{formatMoeda(preview.ipi)}</strong>
                  <span>Frete</span>
                  <strong>{formatMoeda(preview.frete)}</strong>
                </div>
              </section>

              <section className="detalhe-section">
                <div className="detalhe-section-head">
                  <h3 className="detalhe-section-title">Itens e materiais</h3>
                  <span className="detalhe-badge">{preview.produtos.length} item(ns)</span>
                </div>

                <div className="detalhe-table-wrap">
                  <table className="table table-nested">
                    <thead>
                      <tr>
                        <th>Cód. material</th>
                        <th>Qtd entrada</th>
                        <th>Valor unit.</th>
                        <th>Valor item</th>
                        <th>Lotes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.produtos.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="empty">
                            Nenhum item na nota.
                          </td>
                        </tr>
                      ) : (
                        preview.produtos.map((produto, index) => (
                          <tr key={`${produto.codProd}-${index}`}>
                            <td>
                              <strong>{produto.codProd}</strong>
                            </td>
                            <td>{formatNumero(produto.qtdEntrada, 4)}</td>
                            <td>{formatMoeda(produto.cunit)}</td>
                            <td>{formatMoeda(produto.valor)}</td>
                            <td>
                              {produto.loteNF.length === 0 ? (
                                <span className="actions-muted">—</span>
                              ) : (
                                <ul className="lote-list">
                                  {produto.loteNF.map((lote, loteIndex) => (
                                    <li key={`${lote.lote}-${loteIndex}`}>
                                      <strong>{lote.lote || "—"}</strong>
                                      <span>Qtd: {formatNumero(lote.qtdLote, 4)}</span>
                                      {lote.validade ? (
                                        <span>Val: {formatDataHora(lote.validade)}</span>
                                      ) : null}
                                      {lote.observacao ? (
                                        <span className="lote-obs">{lote.observacao}</span>
                                      ) : null}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="detalhe-section detalhe-totals">
                <h3 className="detalhe-section-title">Totais</h3>
                <div className="detalhe-totals-grid">
                  <div className="detalhe-total-card">
                    <span>Soma dos itens</span>
                    <strong>{formatMoeda(somaItens)}</strong>
                  </div>
                  <div className="detalhe-total-card detalhe-total-highlight">
                    <span>Valor total da NF</span>
                    <strong>{formatMoeda(preview.valorTotal)}</strong>
                  </div>
                  <div className="detalhe-total-card">
                    <span>Quantidade de itens</span>
                    <strong>{preview.qtdItens}</strong>
                  </div>
                </div>
              </section>
            </>
          ) : (
            <div className="alert-error detalhe-empty">
              {detalhe.consulta_mensagem ??
                "Não foi possível carregar os itens desta nota no Tasy."}
            </div>
          )}
        </>
      ) : null}
    </Modal>
  );
}
