import { useState } from "react";
import { api } from "../../api";
import { buildQuery, formatData } from "../../lib/format";
import type { NotaConsulta } from "../../types";
import Modal from "../ui/Modal";

interface EmitirEspecificaModalProps {
  open: boolean;
  estabelecimento: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EmitirEspecificaModal({
  open,
  estabelecimento,
  onClose,
  onSuccess,
}: EmitirEspecificaModalProps) {
  const [nrSequencia, setNrSequencia] = useState("");
  const [consulta, setConsulta] = useState<NotaConsulta | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [consultando, setConsultando] = useState(false);
  const [emitindo, setEmitindo] = useState(false);

  const reset = () => {
    setNrSequencia("");
    setConsulta(null);
    setErro(null);
    setMensagem(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const consultar = async () => {
    const valor = nrSequencia.trim();
    if (!valor) {
      setErro("Informe o NR Sequência.");
      return;
    }
    setErro(null);
    setMensagem(null);
    setConsultando(true);
    try {
      const query = buildQuery({ estabelecimento, nr_sequencia: valor });
      const result = await api<NotaConsulta>(`/notas/consultar${query}`);
      setConsulta(result);
      if (!result.encontrada || !result.valido) {
        setErro(result.mensagem ?? "Nota não elegível para emissão.");
      }
    } catch (err) {
      setConsulta(null);
      setErro(err instanceof Error ? err.message : "Falha ao consultar nota");
    } finally {
      setConsultando(false);
    }
  };

  const emitir = async () => {
    const valor = nrSequencia.trim();
    if (!valor || !consulta?.valido) return;

    setErro(null);
    setMensagem(null);
    setEmitindo(true);
    try {
      await api("/notas/emitir-especifica", {
        method: "POST",
        body: { estabelecimento, nr_sequencia: valor },
      });
      setMensagem(`Nota ${consulta.nf ?? valor} enviada para processamento.`);
      onSuccess();
      setTimeout(handleClose, 1200);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao emitir nota");
    } finally {
      setEmitindo(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Emitir nota específica"
      onClose={handleClose}
      wide
      footer={
        <>
          <button type="button" className="btn-ghost" onClick={handleClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => void emitir()}
            disabled={!consulta?.valido || emitindo}
          >
            {emitindo ? "Emitindo..." : "Confirmar emissão"}
          </button>
        </>
      }
    >
      <p className="modal-help">
        Informe o <strong>NR Sequência</strong> do Tasy. A nota será validada quanto à operação
        liberada antes de ser enviada ao PR.
      </p>

      <div className="modal-form-row">
        <label>
          NR Sequência
          <input
            value={nrSequencia}
            onChange={(e) => {
              setNrSequencia(e.target.value);
              setConsulta(null);
              setErro(null);
            }}
            placeholder="Ex: 12345"
          />
        </label>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void consultar()}
          disabled={consultando}
        >
          {consultando ? "Consultando..." : "Consultar"}
        </button>
      </div>

      {consulta?.encontrada ? (
        <div className={`consulta-box ${consulta.valido ? "consulta-ok" : "consulta-erro"}`}>
          <div className="consulta-grid">
            <span>NF</span>
            <strong>{consulta.nf ?? "-"}</strong>
            <span>Operação</span>
            <strong>{consulta.cd_operacao_nf ?? "-"}</strong>
            <span>Liberadas</span>
            <strong>{consulta.operacoes_liberadas.join(", ") || "-"}</strong>
            <span>Fornecedor</span>
            <strong>{consulta.fornecedor ?? "-"}</strong>
            <span>Data NF</span>
            <strong>{formatData(consulta.data_nf)}</strong>
            <span>Itens</span>
            <strong>{consulta.qtd_itens ?? 0}</strong>
          </div>
          {!consulta.valido && consulta.mensagem ? (
            <p className="consulta-msg">{consulta.mensagem}</p>
          ) : null}
        </div>
      ) : null}

      {mensagem ? <div className="alert-success">{mensagem}</div> : null}
      {erro ? <div className="alert-error">{erro}</div> : null}
    </Modal>
  );
}
