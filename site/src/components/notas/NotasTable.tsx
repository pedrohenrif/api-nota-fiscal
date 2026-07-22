import { formatData } from "../../lib/format";
import { formatRetornoPr, podeReemitir } from "../../lib/notas";
import type { NotaStatus } from "../../types";
import { ERRO_TIPO_LABELS } from "../../types";

interface NotasTableProps {
  notas: NotaStatus[];
  carregando?: boolean;
  reemitindoId?: number | null;
  emptyMessage?: string;
  onReemitir?: (nota: NotaStatus) => void;
  onSelectNota?: (nota: NotaStatus) => void;
}

export default function NotasTable({
  notas,
  carregando,
  reemitindoId,
  emptyMessage = "Nenhuma nota encontrada.",
  onReemitir,
  onSelectNota,
}: NotasTableProps) {
  return (
    <div className="table-scroll">
      <table className="table table-notas">
        <thead>
          <tr>
            <th>NF</th>
            <th>NR Sequência</th>
            <th>Fornecedor</th>
            <th>Data NF</th>
            <th>Estabelecimento</th>
            <th>Status</th>
            <th>Tipo erro</th>
            <th>Tent.</th>
            <th>Retorno PR</th>
            <th className="actions-col">Ações</th>
          </tr>
        </thead>
        <tbody>
          {carregando ? (
            <tr>
              <td colSpan={10} className="empty">
                Carregando...
              </td>
            </tr>
          ) : notas.length === 0 ? (
            <tr>
              <td colSpan={10} className="empty">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            notas.map((nota) => {
              const isElegivel = podeReemitir(nota);
              const reemitindo = reemitindoId === nota.id;
              const retorno = formatRetornoPr(nota);

              return (
                <tr
                  key={nota.id}
                  className={onSelectNota ? "table-row-clickable" : undefined}
                  onClick={() => onSelectNota?.(nota)}
                  title={onSelectNota ? "Clique para ver detalhes" : undefined}
                >
                  <td className="cell-nf">{nota.nf}</td>
                  <td className="cell-seq">{nota.nr_sequencia ?? "-"}</td>
                  <td className="cell-fornecedor" title={nota.fornecedor ?? undefined}>
                    {nota.fornecedor ?? "-"}
                  </td>
                  <td className="cell-date">{formatData(nota.data_nf)}</td>
                  <td className="cell-estab">{nota.estabelecimento}</td>
                  <td>
                    <span className={`status status-${nota.status}`}>{nota.status}</span>
                  </td>
                  <td>
                    {nota.erro_tipo ? (
                      <span className={`erro-tipo erro-tipo-${nota.erro_tipo}`}>
                        {ERRO_TIPO_LABELS[nota.erro_tipo] ?? nota.erro_tipo}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="cell-tent">{nota.tentativas}</td>
                  <td
                    className={
                      retorno.kind === "success"
                        ? "pr-success-cell"
                        : retorno.kind === "error"
                          ? "erro-cell"
                          : undefined
                    }
                    title={retorno.title}
                  >
                    {retorno.text}
                  </td>
                  <td className="actions-cell" onClick={(e) => e.stopPropagation()}>
                    {isElegivel ? (
                      <button
                        type="button"
                        className="btn-table"
                        disabled={reemitindo || reemitindoId != null}
                        onClick={() => onReemitir?.(nota)}
                      >
                        {reemitindo ? "..." : "Reemitir"}
                      </button>
                    ) : (
                      <span className="actions-muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
