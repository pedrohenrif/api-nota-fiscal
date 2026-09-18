import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { formatDataHora } from "../lib/format";
import { isDev, isGlobalAdmin } from "../lib/roles";

interface Destinatario {
  id: number;
  estabelecimento: string;
  email: string;
  ativo: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export default function Destinatarios() {
  const { user } = useAuth();
  const canPickEstab = isGlobalAdmin(user?.role) || isDev(user?.role);

  const [estabelecimentos, setEstabelecimentos] = useState<string[]>([]);
  const [selecionado, setSelecionado] = useState("");
  const [itens, setItens] = useState<Destinatario[]>([]);
  const [novoEmail, setNovoEmail] = useState("");
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [editEmail, setEditEmail] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [pronto, setPronto] = useState(false);

  const carregar = useCallback(async (estab?: string) => {
    setCarregando(true);
    setErro(null);
    try {
      const query = estab ? `?estabelecimento=${encodeURIComponent(estab)}` : "";
      const lista = await api<Destinatario[]>(`/destinatarios${query}`);
      setItens(lista);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao carregar destinatários");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    api<string[]>("/estabelecimentos")
      .then((lista) => {
        setEstabelecimentos(lista);
        const inicial = canPickEstab
          ? lista[0] || ""
          : user?.estabelecimento || lista[0] || "";
        setSelecionado(inicial);
        setPronto(true);
      })
      .catch((err) => {
        setErro(err instanceof Error ? err.message : "Erro");
        setCarregando(false);
      });
  }, [canPickEstab, user?.estabelecimento]);

  useEffect(() => {
    if (!pronto) return;
    void carregar(canPickEstab ? selecionado || undefined : undefined);
  }, [carregar, canPickEstab, pronto, selecionado]);

  const adicionar = async () => {
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      await api<Destinatario>("/destinatarios", {
        method: "POST",
        body: {
          email: novoEmail,
          ativo: true,
          ...(canPickEstab ? { estabelecimento: selecionado } : {}),
        },
      });
      setNovoEmail("");
      setMensagem("E-mail adicionado.");
      await carregar(canPickEstab ? selecionado || undefined : undefined);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao adicionar");
    } finally {
      setSalvando(false);
    }
  };

  const salvarEdicao = async (id: number) => {
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      await api<Destinatario>(`/destinatarios/${id}`, {
        method: "PATCH",
        body: { email: editEmail },
      });
      setEditandoId(null);
      setEditEmail("");
      setMensagem("E-mail atualizado.");
      await carregar(canPickEstab ? selecionado || undefined : undefined);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao editar");
    } finally {
      setSalvando(false);
    }
  };

  const alternarAtivo = async (item: Destinatario) => {
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      await api<Destinatario>(`/destinatarios/${item.id}`, {
        method: "PATCH",
        body: { ativo: !item.ativo },
      });
      setMensagem(item.ativo ? "E-mail inativado (não recebe relatório)." : "E-mail reativado.");
      await carregar(canPickEstab ? selecionado || undefined : undefined);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao alterar status");
    } finally {
      setSalvando(false);
    }
  };

  const tituloEstab = canPickEstab ? selecionado : (user?.estabelecimento ?? "—");
  const colCount = canPickEstab ? 5 : 4;

  return (
    <div className="page">
      <h1>Destinatários de e-mail</h1>
      <p className="page-lead">
        Gerencie quem recebe o relatório automático. Não é possível excluir: use{" "}
        <strong>Inativar</strong> para parar o envio sem apagar o cadastro.{" "}
        {canPickEstab
          ? "Admin/dev podem gerenciar todas as unidades."
          : "Você só vê e altera os e-mails do seu estabelecimento."}
      </p>

      <div className="card">
        <div className="row">
          {canPickEstab ? (
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
              Estabelecimento: <strong>{tituloEstab}</strong>
            </div>
          )}
        </div>

        <div className="destinatario-form">
          <label>
            Novo e-mail
            <input
              type="email"
              value={novoEmail}
              onChange={(e) => setNovoEmail(e.target.value)}
              placeholder="nome@empresa.com"
            />
          </label>
          <button
            type="button"
            className="btn-primary"
            disabled={salvando || !novoEmail.trim() || (canPickEstab && !selecionado)}
            onClick={() => void adicionar()}
          >
            Adicionar
          </button>
        </div>

        <p className="help-text">
          Apenas e-mails <strong>ativos</strong> recebem o relatório (quando o envio estiver ligado
          em Configurações). Sem destinatários ativos, o e-mail não é enviado.
        </p>

        {mensagem ? <div className="alert-success">{mensagem}</div> : null}
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Lista — {tituloEstab || "—"}</h2>
            <p className="card-subtitle">
              {itens.length} destinatário(s) · {itens.filter((i) => i.ativo).length} ativo(s)
            </p>
          </div>
        </div>

        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>E-mail</th>
                <th>Status</th>
                {canPickEstab ? <th>Estabelecimento</th> : null}
                <th>Atualizado</th>
                <th className="actions-col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {carregando ? (
                <tr>
                  <td colSpan={colCount} className="empty">
                    Carregando...
                  </td>
                </tr>
              ) : itens.length === 0 ? (
                <tr>
                  <td colSpan={colCount} className="empty">
                    Nenhum e-mail cadastrado para esta unidade.
                  </td>
                </tr>
              ) : (
                itens.map((item) => {
                  const editando = editandoId === item.id;
                  return (
                    <tr key={item.id} className={item.ativo ? undefined : "row-inactive"}>
                      <td>
                        {editando ? (
                          <input
                            type="email"
                            value={editEmail}
                            onChange={(e) => setEditEmail(e.target.value)}
                          />
                        ) : (
                          item.email
                        )}
                      </td>
                      <td>
                        <span className={item.ativo ? "badge-status badge-status--ok" : "badge-status"}>
                          {item.ativo ? "Ativo" : "Inativo"}
                        </span>
                      </td>
                      {canPickEstab ? <td>{item.estabelecimento}</td> : null}
                      <td>{formatDataHora(item.updated_at ?? item.created_at)}</td>
                      <td className="actions-cell">
                        {editando ? (
                          <div className="actions-inline">
                            <button
                              type="button"
                              className="btn-table"
                              disabled={salvando || !editEmail.trim()}
                              onClick={() => void salvarEdicao(item.id)}
                            >
                              Salvar
                            </button>
                            <button
                              type="button"
                              className="btn-ghost"
                              disabled={salvando}
                              onClick={() => {
                                setEditandoId(null);
                                setEditEmail("");
                              }}
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <div className="actions-inline">
                            <button
                              type="button"
                              className="btn-table"
                              disabled={salvando}
                              onClick={() => {
                                setEditandoId(item.id);
                                setEditEmail(item.email);
                              }}
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              className="btn-table"
                              disabled={salvando}
                              onClick={() => void alternarAtivo(item)}
                            >
                              {item.ativo ? "Inativar" : "Reativar"}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
