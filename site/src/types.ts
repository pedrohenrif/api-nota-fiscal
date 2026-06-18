export type Role = "adm" | "usuario";

export interface Usuario {
  id: number;
  username: string;
  role: Role;
  estabelecimento: string | null;
  created_at?: string | null;
}

export interface NotaStatus {
  id: number;
  estabelecimento: string;
  nf: string;
  nr_sequencia?: string | null;
  fornecedor?: string | null;
  data_nf?: string | null;
  status: string;
  tentativas: number;
  erro?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface NotaFilters {
  nf?: string;
  nr_sequencia?: string;
  fornecedor?: string;
  status?: string;
  data_nf_inicio?: string;
  data_nf_fim?: string;
}

export interface NotaConsulta {
  encontrada: boolean;
  valido: boolean;
  mensagem?: string | null;
  nr_sequencia?: string | null;
  nf?: string | null;
  cd_operacao_nf?: number | null;
  operacoes_liberadas: number[];
  fornecedor?: string | null;
  data_nf?: string | null;
  qtd_itens?: number | null;
}

export const NOTA_STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "sent", label: "Enviado" },
  { value: "retry_pending", label: "Aguardando retry" },
  { value: "dead_letter", label: "Falha definitiva" },
  { value: "pending", label: "Pendente" },
] as const;

