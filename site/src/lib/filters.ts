import type { NotaFilters } from "../types";
import { ERRO_TIPO_LABELS } from "../types";

const FILTER_KEYS: (keyof NotaFilters)[] = [
  "nf",
  "nr_sequencia",
  "fornecedor",
  "status",
  "erro_tipo",
  "data_nf_inicio",
  "data_nf_fim",
];

export function countActiveFilters(filtros: NotaFilters): number {
  return FILTER_KEYS.filter((key) => filtros[key]?.trim()).length;
}

export function filterSummary(filtros: NotaFilters): string[] {
  const chips: string[] = [];
  if (filtros.nf?.trim()) chips.push(`NF: ${filtros.nf.trim()}`);
  if (filtros.nr_sequencia?.trim()) chips.push(`Seq.: ${filtros.nr_sequencia.trim()}`);
  if (filtros.fornecedor?.trim()) chips.push(`Fornecedor: ${filtros.fornecedor.trim()}`);
  if (filtros.status?.trim()) chips.push(`Status: ${filtros.status.trim()}`);
  if (filtros.erro_tipo?.trim()) {
    chips.push(`Erro: ${ERRO_TIPO_LABELS[filtros.erro_tipo] ?? filtros.erro_tipo}`);
  }
  if (filtros.data_nf_inicio?.trim()) chips.push(`De: ${filtros.data_nf_inicio.trim()}`);
  if (filtros.data_nf_fim?.trim()) chips.push(`Até: ${filtros.data_nf_fim.trim()}`);
  if (filtros.ordenacao === "data_nf") chips.push("Ordem: Data NF");
  else if (filtros.ordenacao === "nr_sequencia") chips.push("Ordem: NR Sequência");
  return chips;
}
