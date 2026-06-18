import type { NotaFilters } from "../types";

export function countActiveFilters(filtros: NotaFilters): number {
  return Object.values(filtros).filter((v) => v?.trim()).length;
}

export function filterSummary(filtros: NotaFilters): string[] {
  const chips: string[] = [];
  if (filtros.nf?.trim()) chips.push(`NF: ${filtros.nf.trim()}`);
  if (filtros.nr_sequencia?.trim()) chips.push(`Seq.: ${filtros.nr_sequencia.trim()}`);
  if (filtros.fornecedor?.trim()) chips.push(`Fornecedor: ${filtros.fornecedor.trim()}`);
  if (filtros.status?.trim()) chips.push(`Status: ${filtros.status.trim()}`);
  if (filtros.data_nf_inicio?.trim()) chips.push(`De: ${filtros.data_nf_inicio.trim()}`);
  if (filtros.data_nf_fim?.trim()) chips.push(`Até: ${filtros.data_nf_fim.trim()}`);
  return chips;
}
