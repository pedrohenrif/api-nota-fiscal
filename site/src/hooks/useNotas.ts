import { useCallback, useState } from "react";
import { api } from "../api";
import { buildQuery } from "../lib/format";
import type { NotaFilters, NotaStatus } from "../types";

interface UseNotasOptions {
  estabelecimento?: string;
  isAdmin: boolean;
}

export function useNotas({ estabelecimento, isAdmin }: UseNotasOptions) {
  const [notas, setNotas] = useState<NotaStatus[]>([]);
  const [filtros, setFiltros] = useState<NotaFilters>({});
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregarNotas = useCallback(
    async (filtrosOverride?: NotaFilters) => {
      setCarregando(true);
      setErro(null);
      try {
        const ativos = filtrosOverride ?? filtros;
        const query = buildQuery({
          ...(isAdmin && estabelecimento ? { estabelecimento } : {}),
          nf: ativos.nf,
          nr_sequencia: ativos.nr_sequencia,
          fornecedor: ativos.fornecedor,
          status: ativos.status,
          data_nf_inicio: ativos.data_nf_inicio,
          data_nf_fim: ativos.data_nf_fim,
        });
        const lista = await api<NotaStatus[]>(`/notas${query}`);
        setNotas(lista);
      } catch (err) {
        setErro(err instanceof Error ? err.message : "Erro ao carregar notas");
      } finally {
        setCarregando(false);
      }
    },
    [estabelecimento, filtros, isAdmin]
  );

  const aplicarFiltros = useCallback(
    (novos: NotaFilters) => {
      setFiltros(novos);
      void carregarNotas(novos);
    },
    [carregarNotas]
  );

  const limparFiltros = useCallback(() => {
    const vazio: NotaFilters = {};
    setFiltros(vazio);
    void carregarNotas(vazio);
  }, [carregarNotas]);

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
  };
}
