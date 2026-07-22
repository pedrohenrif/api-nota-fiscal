import { useCallback, useState } from "react";
import { api } from "../api";
import { buildQuery } from "../lib/format";
import type { NotaFilters, NotaStatus, NotaStatusPage } from "../types";

interface UseNotasOptions {
  estabelecimento?: string;
  isAdmin: boolean;
}

const PAGE_SIZE = 50;

export function useNotas({ estabelecimento, isAdmin }: UseNotasOptions) {
  const [notas, setNotas] = useState<NotaStatus[]>([]);
  const [filtros, setFiltros] = useState<NotaFilters>({});
  const [filtrosAbertos, setFiltrosAbertos] = useState(true);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [jaPesquisou, setJaPesquisou] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(PAGE_SIZE);

  const carregarNotas = useCallback(
    async (filtrosOverride?: NotaFilters, pageOverride?: number) => {
      const ativos = filtrosOverride ?? filtros;
      if (!jaPesquisou && filtrosOverride === undefined && pageOverride === undefined) {
        return;
      }

      const pageToLoad = pageOverride ?? page;
      setCarregando(true);
      setErro(null);
      try {
        const query = buildQuery({
          ...(isAdmin && estabelecimento ? { estabelecimento } : {}),
          nf: ativos.nf,
          nr_sequencia: ativos.nr_sequencia,
          fornecedor: ativos.fornecedor,
          status: ativos.status,
          erro_tipo: ativos.erro_tipo,
          data_nf_inicio: ativos.data_nf_inicio,
          data_nf_fim: ativos.data_nf_fim,
          page: String(pageToLoad),
          page_size: String(pageSize),
        });
        const result = await api<NotaStatusPage>(`/notas${query}`);
        setNotas(result.items);
        setTotal(result.total);
        setPage(result.page);
        setTotalPages(result.total_pages);
        setJaPesquisou(true);
      } catch (err) {
        setErro(err instanceof Error ? err.message : "Erro ao carregar notas");
      } finally {
        setCarregando(false);
      }
    },
    [estabelecimento, filtros, isAdmin, jaPesquisou, page, pageSize]
  );

  const aplicarFiltros = useCallback(
    (novos: NotaFilters) => {
      setFiltros(novos);
      setPage(1);
      void carregarNotas(novos, 1);
    },
    [carregarNotas]
  );

  const limparFiltros = useCallback(() => {
    setFiltros({});
    setNotas([]);
    setTotal(0);
    setTotalPages(0);
    setPage(1);
    setJaPesquisou(false);
    setErro(null);
  }, []);

  const irParaPagina = useCallback(
    (novaPagina: number) => {
      if (novaPagina < 1 || (totalPages > 0 && novaPagina > totalPages)) return;
      setPage(novaPagina);
      void carregarNotas(undefined, novaPagina);
    },
    [carregarNotas, totalPages]
  );

  return {
    notas,
    filtros,
    filtrosAbertos,
    setFiltrosAbertos,
    carregando,
    erro,
    setErro,
    carregarNotas,
    aplicarFiltros,
    limparFiltros,
    jaPesquisou,
    page,
    pageSize,
    total,
    totalPages,
    irParaPagina,
  };
}
