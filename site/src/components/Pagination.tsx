interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  disabled?: boolean;
  onChange: (page: number) => void;
}

export default function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  disabled,
  onChange,
}: PaginationProps) {
  if (total <= 0) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="pagination">
      <span className="pagination-info">
        {from}–{to} de {total}
      </span>
      <div className="pagination-actions">
        <button
          type="button"
          className="btn-ghost"
          disabled={disabled || page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Anterior
        </button>
        <span className="pagination-page">
          Página {page} / {Math.max(totalPages, 1)}
        </span>
        <button
          type="button"
          className="btn-ghost"
          disabled={disabled || page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
