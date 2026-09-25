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

export function formatRetornoPr(nota: NotaStatus): {
  text: string;
  kind: "success" | "warning" | "error" | "empty";
  title?: string;
} {
  if (isNotaJaExistenteNoPr(nota)) {
    const mensagem =
      nota.pr_mensagem?.trim() ||
      nota.erro?.trim() ||
      "Já existe lançamento no PR com a mesma NF e FORNECEDOR; tratado como integrado.";
    const idSuffix = nota.pr_id != null ? ` (ID PR: ${nota.pr_id})` : "";
    return {
      text: `${mensagem}${idSuffix}`,
      kind: "warning",
      title: nota.pr_id != null ? `ID PR: ${nota.pr_id}` : mensagem,
    };
  }

  if (nota.status === "sent") {
    const mensagem = nota.pr_mensagem?.trim() || "Nota enviada ao PR com sucesso";
    const idSuffix = nota.pr_id != null ? ` (ID PR: ${nota.pr_id})` : "";
    return {
      text: `${mensagem}${idSuffix}`,
      kind: "success",
      title: nota.pr_id != null ? `ID PR: ${nota.pr_id}` : mensagem,
    };
  }

  if (nota.erro?.trim()) {
    return { text: nota.erro, kind: "error", title: nota.erro };
  }

  return { text: "—", kind: "empty" };
}

export function statusDisplay(nota: NotaStatus): { label: string; className: string } {
  if (isNotaJaExistenteNoPr(nota)) {
    return { label: "Já no PR", className: "status-sent_existente" };
  }
  const labels: Record<string, string> = {
    sent: "Enviado",
    sent_existente: "Já no PR",
    retry_pending: "Aguardando retry",
    dead_letter: "Falha definitiva",
    pending: "Pendente",
  };
  return {
    label: labels[nota.status] ?? nota.status,
    className: `status-${nota.status}`,
  };
}
