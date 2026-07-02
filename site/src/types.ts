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
  preview?: NotaPreview | null;
}

export interface LoteNF {
  lote: string;
  validade?: string | null;
  observacao?: string | null;
  qtdLote: number;
}

export interface ProdutoNF {
  codProd: string;
  cunit: number;
  valor: number;
  qtdEntrada: number;
  loteNF: LoteNF[];
}

export interface NotaPreview {
  nf: string;
  serie: string;
  fornecedor: { cnpj: string };
  dataNF?: string | null;
  operador?: string;
  doacao?: boolean;
  vencimento?: string | null;
  dataRecebimento?: string | null;
  desconto?: number;
  ipi?: number;
  frete?: number;
  valorTotal: number;
  qtdItens: number;
  produtos: ProdutoNF[];
}

export interface NotaDetalhe extends NotaStatus {
  cd_operacao_nf?: number | null;
  operacoes_liberadas: number[];
  consulta_mensagem?: string | null;
  preview?: NotaPreview | null;
}

export const NOTA_STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "sent", label: "Enviado" },
  { value: "retry_pending", label: "Aguardando retry" },
  { value: "dead_letter", label: "Falha definitiva" },
  { value: "pending", label: "Pendente" },
] as const;

