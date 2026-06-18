import { api } from "../api";
import type { NotaStatus } from "../types";

export const REEMITIR_STATUS = new Set(["retry_pending", "dead_letter"]);

export function podeReemitir(nota: NotaStatus): boolean {
  return REEMITIR_STATUS.has(nota.status) && Boolean(nota.nr_sequencia?.trim());
}

export function reemitirNota(id: number): Promise<void> {
  return api("/notas/reemitir", { method: "POST", body: { id } });
}
