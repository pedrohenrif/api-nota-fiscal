import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import EmitirEspecificaModal from "../components/notas/EmitirEspecificaModal";
import NotasFilters from "../components/notas/NotasFilters";
import NotasTable from "../components/notas/NotasTable";
import { useNotas } from "../hooks/useNotas";
import { reemitirNota } from "../lib/notas";
import type { NotaStatus } from "../types";

export default function EmitirNota() {
  const { user } = useAuth();
  const isAdmin = user?.role === "adm";

  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);
  const [selecionado, setSelecionado] = useState<string>("");
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [emitindo, setEmitindo] = useState(false);
  const [modalAberto, setModalAberto] = useState(false);
  const [reemitindoId, setReemitindoId] = useState<number | null>(null);

  const {
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
  } = useNotas({ estabelecimento: selecionado, isAdmin });

  useEffect(() => {
    api<string[]>("/estabelecimentos")
      .then((lista) => {
        setEstabelecimentos(lista);
        if (lista.length > 0) setSelecionado(lista[0]);
      })
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro"));
  }, [setErro]);

  useEffect(() => {
    if (selecionado || !isAdmin) void carregarNotas();
  }, [carregarNotas, isAdmin, selecionado]);

  const emitirPendentes = async () => {
    setErro(null);
    setMensagem(null);
    setEmitindo(true);
    try {
      const body = isAdmin ? { estabelecimento: selecionado } : {};
      const result = await api<{
        estabelecimento: string;
        resultado: { published_count?: number };
      }>("/notas/emitir", { method: "POST", body });
      const qtd = result.resultado?.published_count ?? 0;
      setMensagem(
        `Extração acionada para ${result.estabelecimento}. ${qtd} nota(s) pendente(s) publicada(s) na fila.`
      );
      await carregarNotas();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao emitir");
    } finally {
      setEmitindo(false);
    }
  };

  const handleReemitir = async (nota: NotaStatus) => {
    setErro(null);
    setMensagem(null);
    setReemitindoId(nota.id);
    try {
      await reemitirNota(nota.id);
      setMensagem(
        `Nota NF ${nota.nf} (seq. ${nota.nr_sequencia}) reenviada para processamento.`
      );
      await carregarNotas();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao reemitir nota");
    } finally {
      setReemitindoId(null);
    }
  };

  return (
    <div className="page">
      <h1>Emitir Nota</h1>

      <div className="card">
        <div className="row">
          {isAdmin ? (
            <label>
              Estabelecimento
              <select value={selecionado} onChange={(e) => setSelecionado(e.target.value)}>
                {estabelecimentos.map((est) => (
                  <option key={est} value={est}>
                    {est}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <div className="estab-fixed">
              Estabelecimento: <strong>{user?.estabelecimento ?? "-"}</strong>
            </div>
          )}

          <div className="action-group">
            <button className="btn-primary" onClick={() => void emitirPendentes()} disabled={emitindo}>
              {emitindo ? "Processando..." : "Emitir pendentes"}
            </button>
            <button className="btn-secondary" type="button" onClick={() => setModalAberto(true)}>
              Emitir nota específica
            </button>
          </div>
        </div>

        <p className="help-text">
          <strong>Emitir pendentes</strong> busca no Tasy todas as notas elegíveis (filtros de
          operação, datas e estabelecimento) e envia para a fila — não reenvia itens já listados
          abaixo. Cada nota na fila é processada pelo integrador com até 3 tentativas automáticas
          em caso de erro no PR; falhas aparecem na coluna Erro.
        </p>

        {mensagem ? <div className="alert-success">{mensagem}</div> : null}
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Notas recentes</h2>
            <p className="card-subtitle">Histórico de processamento e status de envio ao PR</p>
          </div>
          <button className="btn-ghost" onClick={() => void carregarNotas()}>
            Atualizar
          </button>
        </div>

        <NotasFilters
          filtros={filtros}
          aberto={filtrosAbertos}
          onToggle={() => setFiltrosAbertos((v) => !v)}
          onApply={aplicarFiltros}
          onClear={limparFiltros}
        />

        <NotasTable
          notas={notas}
          carregando={carregando}
          reemitindoId={reemitindoId}
          onReemitir={(nota) => void handleReemitir(nota)}
        />
      </div>

      <EmitirEspecificaModal
        open={modalAberto}
        estabelecimento={isAdmin ? selecionado : (user?.estabelecimento ?? "")}
        onClose={() => setModalAberto(false)}
        onSuccess={() => void carregarNotas()}
      />
    </div>
  );
}
