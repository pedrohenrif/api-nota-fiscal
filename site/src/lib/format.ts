export function formatData(value?: string | null): string {
  if (!value) return "-";
  // Data de calendário (Tasy/DT_EMISSAO): usa YYYY-MM-DD do ISO sem converter fuso.
  // Evita 2026-09-17T00:00:00Z virar 16/09 no horário de Brasília.
  const isoDate = /^(\d{4})-(\d{2})-(\d{2})/.exec(value.trim());
  if (isoDate) {
    const [, year, month, day] = isoDate;
    return `${day}/${month}/${year}`;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("pt-BR");
}

export function formatDataHora(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("pt-BR");
}

export function formatMoeda(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatNumero(value?: number | null, casas = 2): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

export function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const trimmed = value?.trim();
    if (trimmed) search.set(key, trimmed);
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}
