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

export function formatRetornoPr(nota: NotaStatus): {
  text: string;
  kind: "success" | "warning" | "error" | "empty";
  title?: string;
} {
  if (nota.status === "sent_existente") {
    const mensagem =
      nota.pr_mensagem?.trim() ||
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
    // Retrocompat: registros antigos gravados como sent com mensagem de já existente
    if (/ja existe|já existe/i.test(mensagem)) {
      const idSuffix = nota.pr_id != null ? ` (ID PR: ${nota.pr_id})` : "";
      return {
        text: `${mensagem}${idSuffix}`,
        kind: "warning",
        title: nota.pr_id != null ? `ID PR: ${nota.pr_id}` : mensagem,
      };
    }
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
  if (
    nota.status === "sent" &&
    nota.pr_mensagem &&
    /ja existe|já existe/i.test(nota.pr_mensagem)
  ) {
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
