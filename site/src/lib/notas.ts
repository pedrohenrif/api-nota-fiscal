import { api } from "../api";
import type { NotaStatus } from "../types";

export const REEMITIR_STATUS = new Set(["retry_pending", "dead_letter"]);

export function podeReemitir(nota: NotaStatus): boolean {
  return REEMITIR_STATUS.has(nota.status) && Boolean(nota.nr_sequencia?.trim());
}

export function reemitirNota(id: number): Promise<void> {
  return api("/notas/reemitir", { method: "POST", body: { id } });
}

export function formatRetornoPr(nota: NotaStatus): {
  text: string;
  kind: "success" | "error" | "empty";
  title?: string;
} {
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
