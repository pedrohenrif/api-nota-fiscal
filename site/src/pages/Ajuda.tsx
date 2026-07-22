import { useAuth } from "../auth";

export default function Ajuda() {
  const { user } = useAuth();
  const isAdmin = user?.role === "adm";

  return (
    <div className="page">
      <h1>Ajuda</h1>
      <p className="page-lead">
        Guia rápido do painel de integração de notas fiscais (Tasy → PR).
        {isAdmin ? " Conteúdo completo para administrador." : " Foco nas funções do seu estabelecimento."}
      </p>

      <div className="help-sections">
        <section className="card help-card">
          <h2>Dashboard</h2>
          <ul>
            <li>
              Mostra KPIs da integração: total, enviadas com sucesso, retry, dead letter e taxas.
            </li>
            <li>
              Dimensione erros por tipo (sem de-para, sem lote, retorno PR) e acompanhe a evolução
              diária.
            </li>
            <li>
              Use <strong>Exportar CSV</strong> para baixar o relatório completo das notas do
              período (abre no Excel).
            </li>
            {!isAdmin ? (
              <li>Usuário comum vê apenas os dados do próprio estabelecimento.</li>
            ) : (
              <li>Admin pode filtrar por unidade ou ver todas.</li>
            )}
          </ul>
        </section>

        <section className="card help-card">
          <h2>Emitir Nota</h2>
          <ul>
            <li>
              A lista <strong>não carrega sozinha</strong> ao abrir. Use os filtros e clique em{" "}
              <strong>Aplicar filtros</strong>.
            </li>
            <li>
              Você pode ordenar por <strong>NR Sequência</strong> ou <strong>Data NF</strong>{" "}
              (sempre do mais recente/maior para o menor).
            </li>
            <li>
              <strong>Emitir pendentes</strong> busca no Tasy as notas elegíveis e coloca na fila
              para o PR.
            </li>
            <li>
              <strong>Emitir nota específica</strong> envia uma sequência escolhida.
            </li>
            <li>
              Clique em uma linha para ver itens, lotes e status de de-para. Use{" "}
              <strong>Reemitir</strong> quando a nota estiver com erro e a causa já tiver sido
              corrigida.
            </li>
          </ul>
        </section>

        <section className="card help-card">
          <h2>Tipos de erro comuns</h2>
          <ul>
            <li>
              <strong>Sem de-para</strong> — material do Tasy sem vínculo no PR. Cadastre o de-para
              e reemitir.
            </li>
            <li>
              <strong>Sem lote</strong> — item exige lote e não veio informado no Tasy.
            </li>
            <li>
              <strong>Retorno PR</strong> — a API do PR recusou (ex.: NF já integrada, validação).
            </li>
          </ul>
        </section>

        <section className="card help-card">
          <h2>E-mails do relatório</h2>
          <ul>
            <li>
              Na aba <strong>Destinatários</strong> você adiciona, edita ou remove quem recebe o
              relatório automático.
            </li>
            {!isAdmin ? (
              <li>Usuários comuns só gerenciam os e-mails do próprio estabelecimento.</li>
            ) : (
              <li>Admin escolhe a unidade e gerencia os e-mails de cada uma.</li>
            )}
            <li>
              O relatório traz: notas integradas (uma vez), erros de PR (uma vez), pendências sem
              de-para/lote (podem repetir até resolver).
            </li>
            {isAdmin ? (
              <li>
                Ligar/desligar o envio automático por unidade fica em{" "}
                <strong>Configurações</strong> (somente admin).
              </li>
            ) : (
              <li>
                Ligar/desligar o disparo automático é feito pelo administrador em Configurações.
              </li>
            )}
          </ul>
        </section>

        {isAdmin ? (
          <>
            <section className="card help-card">
              <h2>Configurações (somente admin)</h2>
              <ul>
                <li>
                  <strong>Scheduler</strong> — liga/desliga a extração automática da unidade.
                </li>
                <li>
                  <strong>Relatório</strong> — liga/desligar o e-mail automático da unidade.
                </li>
                <li>
                  É possível <strong>enviar relatório agora</strong> para testar o SMTP e a
                  classificação.
                </li>
              </ul>
            </section>

            <section className="card help-card">
              <h2>Logs e Acessos (somente admin)</h2>
              <ul>
                <li>
                  <strong>Logs</strong> — histórico de processamento das notas (status, tipo de
                  erro, retorno PR), com filtros e paginação.
                </li>
                <li>
                  <strong>Acessos</strong> — auditoria de quem entrou no painel: IP, usuário, ação,
                  data e status HTTP. Use filtros de data/perfil/ação para investigar.
                </li>
                <li>
                  <strong>Usuários</strong> — cadastro de logins e vínculo com estabelecimento.
                </li>
              </ul>
            </section>
          </>
        ) : (
          <section className="card help-card">
            <h2>O que o usuário comum não vê</h2>
            <ul>
              <li>Configurações de ligar/desligar API e e-mail automático.</li>
              <li>Logs globais de processamento e auditoria de acessos/IP.</li>
              <li>Cadastro de usuários de outras unidades.</li>
            </ul>
          </section>
        )}

        <section className="card help-card">
          <h2>Dúvidas rápidas</h2>
          <ul>
            <li>
              <strong>A nota some da lista?</strong> Só aparece após aplicar filtros. Limpar
              filtros esvazia a tabela até nova pesquisa.
            </li>
            <li>
              <strong>Recebi o mesmo e-mail várias vezes?</strong> Sem de-para/lote continua
              avisando. Integrada com sucesso e retorno PR entram só uma vez.
            </li>
            <li>
              <strong>Tabela cortada na tela?</strong> Role horizontalmente; a coluna Ações fica
              fixa à direita.
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
