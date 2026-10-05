import { api } from "../api";
import type { NotaDetalhe, NotaStatus } from "../types";

export const REEMITIR_STATUS = new Set(["retry_pending", "dead_letter"]);

export function podeReemitir(nota: NotaStatus): boolean {
  return REEMITIR_STATUS.has(nota.status) && Boolean(nota.nr_sequencia?.trim());
}

export function reemitirNota(id: number): Promise<void> {
  return api("/notas/reemitir", { method: "POST", body: { id } });
}

export function atualizarNotaDoTasy(
  id: number,
  reenviar = false
): Promise<NotaDetalhe> {
  return api<NotaDetalhe>(`/notas/${id}/atualizar-tasy`, {
    method: "POST",
    body: { reenviar },
  });
}

/** Normaliza acentos/caixa para detectar "já existe" em registros antigos. */
function textoIndicaJaExistiaNoPr(...parts: Array<string | null | undefined>): boolean {
  const raw = parts.filter(Boolean).join(" ");
  if (!raw.trim()) return false;
  const normalized = raw
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase();
  return (
    normalized.includes("ja existe") ||
    normalized.includes("jaexistiano pr") ||
    normalized.includes("ja_existia") ||
    normalized.includes("jaexistiano")
  );
}

export function isNotaJaExistenteNoPr(nota: NotaStatus): boolean {
  if (nota.status === "sent_existente") return true;
  if (nota.status !== "sent") return false;
  return textoIndicaJaExistiaNoPr(nota.pr_mensagem, nota.erro);
}

function isCanalHrba(nota: NotaStatus): boolean {
  return (nota.estabelecimento || "").trim().toUpperCase() === "HRBA";
}

/** Rótulo do id persistido em pr_id: no HRBA é nr_sequencia Tasy destino. */
function formatIdIntegracao(nota: NotaStatus): { suffix: string; title: string } | null {
  if (nota.pr_id == null) return null;
  if (isCanalHrba(nota)) {
    return {
      suffix: ` (NR Seq HRBA: ${nota.pr_id})`,
      title: `NR Seq HRBA: ${nota.pr_id}`,
    };
  }
  return {
    suffix: ` (ID PR: ${nota.pr_id})`,
    title: `ID PR: ${nota.pr_id}`,
  };
}

export function formatRetornoPr(nota: NotaStatus): {
  text: string;
  kind: "success" | "warning" | "error" | "empty";
  title?: string;
} {
  const idInfo = formatIdIntegracao(nota);
  const hrba = isCanalHrba(nota);

  if (isNotaJaExistenteNoPr(nota)) {
    const mensagem =
      nota.pr_mensagem?.trim() ||
      nota.erro?.trim() ||
      (hrba
        ? "Já existe lançamento no HRBA com a mesma NF e FORNECEDOR; tratado como integrado."
        : "Já existe lançamento no PR com a mesma NF e FORNECEDOR; tratado como integrado.");
    return {
      text: `${mensagem}${idInfo?.suffix ?? ""}`,
      kind: "warning",
      title: idInfo?.title ?? mensagem,
    };
  }

  if (nota.status === "sent") {
    const mensagem =
      nota.pr_mensagem?.trim() ||
      (hrba ? "Nota integrada no HRBA com sucesso" : "Nota enviada ao PR com sucesso");
    return {
      text: `${mensagem}${idInfo?.suffix ?? ""}`,
      kind: "success",
      title: idInfo?.title ?? mensagem,
    };
  }

  if (nota.erro?.trim()) {
    return { text: nota.erro, kind: "error", title: nota.erro };
  }

  return { text: "—", kind: "empty" };
}

export function statusDisplay(nota: NotaStatus): { label: string; className: string } {
  if (isNotaJaExistenteNoPr(nota)) {
    return {
      label: isCanalHrba(nota) ? "Já no HRBA" : "Já no PR",
      className: "status-sent_existente",
    };
  }
  const labels: Record<string, string> = {
    sent: "Enviado",
    sent_existente: isCanalHrba(nota) ? "Já no HRBA" : "Já no PR",
    retry_pending: "Aguardando retry",
    dead_letter: "Falha definitiva",
    pending: "Pendente",
  };
  return {
    label: labels[nota.status] ?? nota.status,
    className: `status-${nota.status}`,
  };
}
