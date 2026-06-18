import { useEffect, useState } from "react";
import type { NotaFilters } from "../../types";
import { NOTA_STATUS_OPTIONS } from "../../types";
import { countActiveFilters, filterSummary } from "../../lib/filters";

interface NotasFiltersProps {
  filtros: NotaFilters;
  aberto: boolean;
  onToggle: () => void;
  onApply: (filtros: NotaFilters) => void;
  onClear: () => void;
}

export default function NotasFilters({
  filtros,
  aberto,
  onToggle,
  onApply,
  onClear,
}: NotasFiltersProps) {
  const [draft, setDraft] = useState<NotaFilters>(filtros);
  const ativos = countActiveFilters(filtros);
  const chips = filterSummary(filtros);

  useEffect(() => {
    if (aberto) setDraft(filtros);
  }, [aberto, filtros]);

  const update = (field: keyof NotaFilters, value: string) => {
    setDraft((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <section className="filters-section">
      <div className="filters-toolbar">
        <button
          type="button"
          className={`filters-toggle${aberto ? " filters-toggle--open" : ""}`}
          onClick={onToggle}
          aria-expanded={aberto}
        >
          <span className="filters-toggle-icon" aria-hidden="true">
            ▾
          </span>
          Filtros
          {ativos > 0 ? <span className="filters-badge">{ativos}</span> : null}
        </button>

        {!aberto && chips.length > 0 ? (
          <div className="filters-chips">
            {chips.map((chip) => (
              <span key={chip} className="filter-chip">
                {chip}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {aberto ? (
        <div className="filters-panel">
          <p className="filters-intro">
            Refine a lista por qualquer combinação de campos abaixo.
          </p>
          <div className="filters-grid">
            <label className="filter-field">
              <span className="filter-label">NF</span>
              <input
                value={draft.nf ?? ""}
                onChange={(e) => update("nf", e.target.value)}
                placeholder="Número da nota"
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">NR Sequência</span>
              <input
                value={draft.nr_sequencia ?? ""}
                onChange={(e) => update("nr_sequencia", e.target.value)}
                placeholder="Ex: 12345"
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">Fornecedor</span>
              <input
                value={draft.fornecedor ?? ""}
                onChange={(e) => update("fornecedor", e.target.value)}
                placeholder="CNPJ ou parte"
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">Status</span>
              <select
                value={draft.status ?? ""}
                onChange={(e) => update("status", e.target.value)}
              >
                {NOTA_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value || "all"} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="filter-field">
              <span className="filter-label">Data NF — de</span>
              <input
                type="date"
                value={draft.data_nf_inicio ?? ""}
                onChange={(e) => update("data_nf_inicio", e.target.value)}
              />
            </label>
            <label className="filter-field">
              <span className="filter-label">Data NF — até</span>
              <input
                type="date"
                value={draft.data_nf_fim ?? ""}
                onChange={(e) => update("data_nf_fim", e.target.value)}
              />
            </label>
          </div>
          <div className="filters-actions">
            <button type="button" className="btn-primary" onClick={() => onApply(draft)}>
              Aplicar filtros
            </button>
            <button type="button" className="btn-ghost" onClick={onClear}>
              Limpar tudo
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
