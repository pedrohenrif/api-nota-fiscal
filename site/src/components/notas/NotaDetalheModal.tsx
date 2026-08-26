import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { formatData, formatDataHora, formatMoeda, formatNumero } from "../../lib/format";
import { atualizarNotaDoTasy, podeReemitir } from "../../lib/notas";
import type { DeparaStatus, NotaDetalhe, NotaStatus, ProdutoNF } from "../../types";
import Modal from "../ui/Modal";

interface NotaDetalheModalProps {
  nota: NotaStatus | null;
  onClose: () => void;
  onAtualizado?: () => void;
}

function DeparaBadge({ depara }: { depara?: DeparaStatus | null }) {
  if (!depara) {
    return <span className="depara-badge depara-pendente">—</span>;
  }

  if (depara.status === "ok") {
    return (
      <span
        className="depara-badge depara-ok"
        title={`Código PR: ${depara.codProdPR}${
          depara.controleDeLote ? " · Controle de lote: sim" : " · Controle de lote: não"
        }`}
      >
        OK → {depara.codProdPR}
        {depara.controleDeLote ? " · lote" : ""}
      </span>
    );
  }

  if (depara.status === "vazio") {
    return (
      <span className="depara-badge depara-vazio" title={depara.mensagem ?? undefined}>
        Sem vínculo no PR
      </span>
    );
  }

  return (
    <span className="depara-badge depara-erro" title={depara.mensagem ?? undefined}>
      Erro no de-para
    </span>
  );
}

function itemComFalhaDepara(produto: ProdutoNF): boolean {
  return produto.depara != null && produto.depara.status !== "ok";
}

export default function NotaDetalheModal({
  nota,
  onClose,
  onAtualizado,
}: NotaDetalheModalProps) {
  const [detalhe, setDetalhe] = useState<NotaDetalhe | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [atualizando, setAtualizando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (!nota) {
      setDetalhe(null);
      setErro(null);
      setInfo(null);
      return;
    }

    let ativo = true;
    setCarregando(true);
    setErro(null);
    setInfo(null);
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
  const integradaPr = detalhe?.status === "sent";
  const podeFalhou = detalhe ? podeReemitir(detalhe) : false;
  const msgConsulta = detalhe?.consulta_mensagem ?? "";
  const msgTasyIntegrada = /dt_integracao|integrada no tasy/i.test(msgConsulta);
  const somaItens = useMemo(
    () => (preview?.produtos ?? []).reduce((acc, item) => acc + (item.valor ?? 0), 0),
    [preview]
  );
  const divergenciaTotais =
    preview != null && Math.abs(somaItens - (preview.valorTotal ?? 0)) > 0.009;

  const itensSemDepara = useMemo(
    () => (preview?.produtos ?? []).filter(itemComFalhaDepara),
    [preview]
  );

  const atualizarDoTasy = async (reenviar: boolean) => {
    if (!nota) return;
    setAtualizando(true);
    setErro(null);
    setInfo(null);
    try {
      const result = await atualizarNotaDoTasy(nota.id, reenviar);
      setDetalhe(result);
      setInfo(
        reenviar
          ? "Dados atualizados do Tasy e nota reenviada para a fila."
          : "Dados atualizados do Tasy no painel. Se a nota estiver com erro, use Reenviar para processar de novo."
      );
      onAtualizado?.();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao atualizar do Tasy");
    } finally {
      setAtualizando(false);
    }
  };

  return (
    <Modal
      open={nota != null}
      title={nota ? `Nota fiscal ${nota.nf}` : "Detalhes da nota"}
      onClose={onClose}
      xl
      footer={
        <>
          <button
            type="button"
            className="btn-ghost"
            disabled={atualizando || carregando || !nota?.nr_sequencia}
            onClick={() => void atualizarDoTasy(false)}
            title="Puxa NF, fornecedor, data e itens atuais do Tasy e atualiza o painel"
          >
            {atualizando ? "Atualizando..." : "Atualizar do Tasy"}
          </button>
          {podeFalhou ? (
            <button
              type="button"
              className="btn-ghost"
              disabled={atualizando || carregando}
              onClick={() => void atualizarDoTasy(true)}
              title="Atualiza do Tasy e republica na fila de integração"
            >
              Atualizar e reenviar
            </button>
          ) : null}
          <button type="button" className="btn-primary" onClick={onClose}>
            Fechar
          </button>
        </>
      }
    >
      {carregando ? (
        <p className="detalhe-loading">Carregando detalhes e validando de-para no PR...</p>
      ) : !detalhe && erro ? (
        <div className="alert-error">{erro}</div>
      ) : detalhe ? (
        <>
          {erro ? <div className="alert-error">{erro}</div> : null}
          {info ? <div className="alert-success">{info}</div> : null}
          <div className="detalhe-status-row">
            <span className={`status status-${detalhe.status}`}>{detalhe.status}</span>
            <span className="detalhe-meta">
              Tentativas: <strong>{detalhe.tentativas}</strong>
            </span>
            {detalhe.erro && !integradaPr ? (
              <span className="detalhe-erro-inline" title={detalhe.erro}>
                {detalhe.erro}
              </span>
            ) : null}
          </div>

          {integradaPr ? (
            <div className="alert-success">
              Integrada no PR com sucesso.
              {msgTasyIntegrada ? (
                <p className="depara-resumo-hint">
                  Write-back no Tasy concluído (`dt_integracao` preenchida).
                </p>
              ) : null}
              {detalhe.pr_id ? (
                <p className="depara-resumo-hint">PR ID: {detalhe.pr_id}</p>
              ) : null}
            </div>
          ) : null}

          {detalhe.depara_resumo && detalhe.depara_resumo.falha > 0 ? (
            <div className="depara-resumo-alert">
              <strong>
                {detalhe.depara_resumo.falha} de {detalhe.depara_resumo.total} item(ns) sem
                de-para no PR
              </strong>
              <p>
                Materiais pendentes:{" "}
                {itensSemDepara.map((item) => item.codProd).join(", ") || "—"}
              </p>
            </div>
          ) : detalhe.depara_resumo && detalhe.depara_resumo.total > 0 ? (
            <div className="alert-success depara-resumo-ok">
              De-para validado: todos os {detalhe.depara_resumo.total} item(ns) possuem vínculo no
              PR.
              {detalhe.erro?.toLowerCase().includes("de-para") ? (
                <p className="depara-resumo-hint">
                  O erro exibido acima é da última tentativa de envio (retry antigo). Pode
                  reemitir a nota.
                </p>
              ) : null}
            </div>
          ) : null}

          {!integradaPr && detalhe.consulta_mensagem && !preview ? (
            <div className="alert-error">{detalhe.consulta_mensagem}</div>
          ) : null}

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
            <p className="detalhe-fonte">Dados consultados em tempo real no Tasy (Oracle).</p>
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
                        <th>Cód. material (Tasy)</th>
                        <th>De-para PR</th>
                        <th>Qtd entrada</th>
                        <th>Valor unit.</th>
                        <th>Valor item</th>
                        <th>Lotes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.produtos.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="empty">
                            Nenhum item na nota.
                          </td>
                        </tr>
                      ) : (
                        preview.produtos.map((produto, index) => (
                          <tr
                            key={`${produto.codProd}-${index}`}
                            className={itemComFalhaDepara(produto) ? "detalhe-row-erro" : undefined}
                          >
                            <td>
                              <strong>{produto.codProd}</strong>
                            </td>
                            <td>
                              <DeparaBadge depara={produto.depara} />
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
                {divergenciaTotais ? (
                  <div className="alert-error" style={{ marginBottom: 12 }}>
                    Soma dos itens ({formatMoeda(somaItens)}) diverge do total da NF (
                    {formatMoeda(preview.valorTotal)}). Confira o ajuste no Tasy e use{" "}
                    <strong>Atualizar do Tasy</strong>
                    {podeFalhou ? " / Atualizar e reenviar" : ""}.
                  </div>
                ) : null}
                <div className="detalhe-totals-grid">
                  <div className="detalhe-total-card">
                    <span>Soma dos itens</span>
                    <strong>{formatMoeda(somaItens)}</strong>
                  </div>
                  <div
                    className={`detalhe-total-card detalhe-total-highlight${
                      divergenciaTotais ? " detalhe-total-divergente" : ""
                    }`}
                  >
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
            <div className={`detalhe-empty ${integradaPr ? "alert-success" : "alert-error"}`}>
              {integradaPr
                ? "Integrada no PR. Não foi possível carregar os itens no Tasy neste momento."
                : detalhe.consulta_mensagem ??
                  "Não foi possível carregar os itens desta nota no Tasy."}
            </div>
          )}
        </>
      ) : null}
    </Modal>
  );
}
