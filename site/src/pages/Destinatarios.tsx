import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { formatDataHora } from "../lib/format";

interface Destinatario {
  id: number;
  estabelecimento: string;
  email: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export default function Destinatarios() {
  const { user } = useAuth();
  const isAdmin = user?.role === "adm";

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
        const inicial = isAdmin
          ? lista[0] || ""
          : user?.estabelecimento || lista[0] || "";
        setSelecionado(inicial);
        setPronto(true);
      })
      .catch((err) => {
        setErro(err instanceof Error ? err.message : "Erro");
        setCarregando(false);
      });
  }, [isAdmin, user?.estabelecimento]);

  useEffect(() => {
    if (!pronto) return;
    void carregar(isAdmin ? selecionado || undefined : undefined);
  }, [carregar, isAdmin, pronto, selecionado]);

  const adicionar = async () => {
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      await api<Destinatario>("/destinatarios", {
        method: "POST",
        body: {
          email: novoEmail,
          ...(isAdmin ? { estabelecimento: selecionado } : {}),
        },
      });
      setNovoEmail("");
      setMensagem("E-mail adicionado.");
      await carregar(isAdmin ? selecionado || undefined : undefined);
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
      await carregar(isAdmin ? selecionado || undefined : undefined);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao editar");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id: number, email: string) => {
    if (!window.confirm(`Excluir o e-mail ${email}?`)) return;
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      await api(`/destinatarios/${id}`, { method: "DELETE" });
      setMensagem("E-mail excluído.");
      await carregar(isAdmin ? selecionado || undefined : undefined);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao excluir");
    } finally {
      setSalvando(false);
    }
  };

  const tituloEstab = isAdmin ? selecionado : (user?.estabelecimento ?? "—");

  return (
    <div className="page">
      <h1>Destinatários de e-mail</h1>
      <p className="page-lead">
        Gerencie quem recebe o relatório automático de notas.{" "}
        {isAdmin
          ? "Admin pode gerenciar todas as unidades."
          : "Você só vê e altera os e-mails do seu estabelecimento."}
      </p>

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
            disabled={salvando || !novoEmail.trim() || (isAdmin && !selecionado)}
            onClick={() => void adicionar()}
          >
            Adicionar
          </button>
        </div>

        <p className="help-text">
          Esses e-mails recebem o disparo do relatório (quando o envio estiver ligado em
          Configurações, exclusivo do admin). Sem destinatários, o e-mail não é enviado.
        </p>

        {mensagem ? <div className="alert-success">{mensagem}</div> : null}
        {erro ? <div className="alert-error">{erro}</div> : null}
      </div>

      <div className="card card-table">
        <div className="card-header">
          <div>
            <h2>Lista — {tituloEstab || "—"}</h2>
            <p className="card-subtitle">{itens.length} destinatário(s)</p>
          </div>
        </div>

        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>E-mail</th>
                {isAdmin ? <th>Estabelecimento</th> : null}
                <th>Atualizado</th>
                <th className="actions-col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {carregando ? (
                <tr>
                  <td colSpan={isAdmin ? 4 : 3} className="empty">
                    Carregando...
                  </td>
                </tr>
              ) : itens.length === 0 ? (
                <tr>
                  <td colSpan={isAdmin ? 4 : 3} className="empty">
                    Nenhum e-mail cadastrado para esta unidade.
                  </td>
                </tr>
              ) : (
                itens.map((item) => {
                  const editando = editandoId === item.id;
                  return (
                    <tr key={item.id}>
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
                      {isAdmin ? <td>{item.estabelecimento}</td> : null}
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
                              className="btn-ghost btn-danger-text"
                              disabled={salvando}
                              onClick={() => void excluir(item.id, item.email)}
                            >
                              Excluir
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
