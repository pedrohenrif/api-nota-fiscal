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
  erro_tipo?: string | null;
  pr_id?: number | null;
  pr_mensagem?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type NotaOrdenacao = "nr_sequencia" | "data_nf";

export interface NotaFilters {
  nf?: string;
  nr_sequencia?: string;
  fornecedor?: string;
  status?: string;
  erro_tipo?: string;
  data_nf_inicio?: string;
  data_nf_fim?: string;
  ordenacao?: NotaOrdenacao;
}

export const NOTA_ORDENACAO_OPTIONS = [
  { value: "nr_sequencia", label: "NR Sequência (maior → menor)" },
  { value: "data_nf", label: "Data NF (mais recente)" },
] as const;

export interface NotaStatusPage {
  items: NotaStatus[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AccessAuditLog {
  id: number;
  created_at?: string | null;
  username?: string | null;
  role?: string | null;
  estabelecimento?: string | null;
  ip: string;
  method: string;
  path: string;
  action: string;
  status_code: number;
  detail?: string | null;
  user_agent?: string | null;
}

export interface AccessAuditPage {
  items: AccessAuditLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface AccessIpSummaryItem {
  ip: string;
  acessos: number;
  ultimo_acesso?: string | null;
  ultimo_usuario?: string | null;
}

export interface AccessIpSummary {
  total_acessos: number;
  ips_unicos: number;
  usuarios_unicos: number;
  por_ip: AccessIpSummaryItem[];
}

export interface NotaConsultaLocalEstoque {
  cd_local_estoque: string;
  qtd_itens: number;
}

export interface NotaConsultaItemDiagnostico {
  nr_item_nf: string;
  cd_material: string;
  ds_reduzida?: string | null;
  cd_local_estoque?: number | null;
  elegivel: boolean;
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
  qtd_itens_total?: number | null;
  locais_estoque?: NotaConsultaLocalEstoque[];
  itens_diagnostico?: NotaConsultaItemDiagnostico[];
  preview?: NotaPreview | null;
}

export interface LoteNF {
  lote: string;
  validade?: string | null;
  observacao?: string | null;
  qtdLote: number;
}

export interface DeparaStatus {
  status: "ok" | "vazio" | "erro";
  codProdTasy: string;
  codProdPR?: string | null;
  controleDeLote?: boolean;
  mensagem?: string | null;
}

export interface DeparaResumo {
  total: number;
  ok: number;
  falha: number;
}

export interface ProdutoNF {
  codProd: string;
  cunit: number;
  valor: number;
  qtdEntrada: number;
  loteNF: LoteNF[];
  depara?: DeparaStatus | null;
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
  depara_resumo?: DeparaResumo | null;
}

export const NOTA_STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "sent", label: "Enviado" },
  { value: "retry_pending", label: "Aguardando retry" },
  { value: "dead_letter", label: "Falha definitiva" },
  { value: "pending", label: "Pendente" },
] as const;

export const ERRO_TIPO_OPTIONS = [
  { value: "", label: "Todos os tipos" },
  { value: "sem_depara", label: "Sem de-para" },
  { value: "sem_lote", label: "Sem lote" },
  { value: "retorno_pr", label: "Retorno PR" },
  { value: "outro", label: "Outro" },
] as const;

export const ERRO_TIPO_LABELS: Record<string, string> = {
  sem_depara: "Sem de-para",
  sem_lote: "Sem lote",
  retorno_pr: "Retorno PR",
  outro: "Outro",
};

