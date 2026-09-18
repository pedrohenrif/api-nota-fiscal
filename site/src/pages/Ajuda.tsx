import { useAuth } from "../auth";
import {
  canManageConfig,
  canManageUsers,
  canSeeAcesso,
  canSeeFilas,
  isDev,
  isGlobalAdmin,
  roleLabel,
} from "../lib/roles";

export default function Ajuda() {
  const { user } = useAuth();
  const role = user?.role;
  const isAdmin = isGlobalAdmin(role);
  const localManager = canManageUsers(role);
  const seesFilas = canSeeFilas(role);
  const seesAcesso = canSeeAcesso(role);
  const config = canManageConfig(role);

  return (
    <div className="page">
      <h1>Ajuda</h1>
      <p className="page-lead">
        Guia do painel de integração de notas (Tasy → PR). Seu perfil atual:{" "}
        <strong>{roleLabel(role)}</strong>
        {user?.estabelecimento ? ` · ${user.estabelecimento}` : ""}.
      </p>

      <div className="help-sections">
        <section className="card help-card">
          <h2>Dashboard</h2>
          <ul>
            <li>
              Abre com o <strong>mês corrente</strong> (dia 1 até o último dia). Altere as datas
              se precisar de outro período.
            </li>
            <li>
              KPIs: total, enviadas, retry, dead letter, tipos de erro e evolução diária.
            </li>
            <li>
              Use <strong>Exportar CSV</strong> para baixar o relatório do período.
            </li>
            {seesFilas ? (
              <li>
                Bloco <strong>Filas e processor</strong> mostra fila RabbitMQ, dead letter e
                saúde do consumer/circuit breaker (somente dev).
              </li>
            ) : null}
            {!isAdmin && !isDev(role) ? (
              <li>Você vê apenas os dados do próprio estabelecimento.</li>
            ) : (
              <li>Admin/dev podem filtrar por unidade ou ver todas.</li>
            )}
          </ul>
        </section>

        <section className="card help-card">
          <h2>Emitir Nota</h2>
          <ul>
            <li>
              A lista <strong>não carrega sozinha</strong>. Use os filtros e clique em{" "}
              <strong>Aplicar filtros</strong>.
            </li>
            <li>
              Ordene por <strong>NR Sequência</strong> ou <strong>Data NF</strong>.
            </li>
            <li>
              <strong>Emitir pendentes</strong> busca no Tasy e coloca na fila do PR.{" "}
              <strong>Emitir nota específica</strong> envia uma sequência.
            </li>
            <li>
              Clique na linha para ver itens/lotes/de-para. Use <strong>Reemitir</strong> após
              corrigir a causa do erro.
            </li>
          </ul>
        </section>

        <section className="card help-card">
          <h2>Tipos de erro comuns</h2>
          <ul>
            <li>
              <strong>Sem de-para</strong> — material do Tasy sem vínculo no PR. Cadastre e
              reemitir.
            </li>
            <li>
              <strong>Sem lote</strong> — item exige lote e não veio no Tasy.
            </li>
            <li>
              <strong>Retorno PR</strong> — a API do PR recusou (ex.: NF já integrada).
            </li>
            <li>
              <strong>Timeout / circuit aberto</strong> — PR lento ou indisponível; o processor
              pausa e retoma sozinho. Acompanhe no Dashboard (filas).
            </li>
          </ul>
        </section>

        <section className="card help-card">
          <h2>E-mails do relatório</h2>
          <ul>
            <li>
              Em <strong>Destinatários</strong> você adiciona, edita, <strong>inativa</strong> ou
              remove quem recebe o relatório.
            </li>
            <li>
              Inativar mantém o cadastro, mas o e-mail deixa de receber até reativar.
            </li>
            <li>
              Relatório: integradas e erros de PR (uma vez); pendências de-para/lote (podem
              repetir até resolver).
            </li>
            {config ? (
              <li>
                Ligar/desligar o envio automático por unidade fica em{" "}
                <strong>Configurações</strong>.
              </li>
            ) : (
              <li>Ligar/desligar o disparo automático é feito pelo administrador global.</li>
            )}
          </ul>
        </section>

        <section className="card help-card">
          <h2>Senha e login</h2>
          <ul>
            <li>
              Cada usuário pode ter um <strong>e-mail</strong> cadastrado (aba Usuários, se você
              gerencia logins).
            </li>
            <li>
              Em <strong>Esqueci minha senha</strong> no login: informe o e-mail, receba o código
              e defina a nova senha.
            </li>
            <li>Sem e-mail cadastrado, o reset por código não funciona.</li>
          </ul>
        </section>

        {localManager ? (
          <section className="card help-card">
            <h2>Usuários</h2>
            <ul>
              <li>
                {isAdmin
                  ? "Admin global cria qualquer perfil (usuário, adm local, adm, dev) em qualquer unidade."
                  : "Adm local cria usuários e outros adm locais só no próprio estabelecimento."}
              </li>
              <li>
                Cadastre o e-mail do usuário para permitir recuperação de senha.
              </li>
              <li>
                Perfis: <strong>usuário</strong> (operação), <strong>adm local</strong> (unidade),{" "}
                <strong>adm</strong> (global), <strong>dev</strong> (auditoria/filas).
              </li>
            </ul>
          </section>
        ) : null}

        <section className="card help-card">
          <h2>Logs</h2>
          <ul>
            <li>
              Histórico de processamento (status, tipo de erro, retorno PR), com filtros e
              paginação.
            </li>
            {!isAdmin && !isDev(role) ? (
              <li>Escopo limitado ao seu estabelecimento.</li>
            ) : (
              <li>Admin/dev veem todas as unidades (com filtro opcional).</li>
            )}
          </ul>
        </section>

        {seesAcesso ? (
          <section className="card help-card">
            <h2>Acessos (somente dev)</h2>
            <ul>
              <li>
                Auditoria de quem entrou no painel: IP, usuário, ação, data e status HTTP.
              </li>
              <li>Use filtros de data/perfil/ação para investigar.</li>
            </ul>
          </section>
        ) : null}

        {config ? (
          <section className="card help-card">
            <h2>Configurações (somente admin)</h2>
            <ul>
              <li>
                <strong>Scheduler</strong> — liga/desliga a extração automática da unidade.
              </li>
              <li>
                <strong>Relatório</strong> — liga/desliga o e-mail automático.
              </li>
              <li>
                É possível <strong>enviar relatório agora</strong> para testar SMTP e classificação.
              </li>
            </ul>
          </section>
        ) : null}

        <section className="card help-card">
          <h2>Dúvidas rápidas</h2>
          <ul>
            <li>
              <strong>A nota some da lista?</strong> Só aparece após aplicar filtros.
            </li>
            <li>
              <strong>Recebi o mesmo e-mail várias vezes?</strong> Sem de-para/lote continua
              avisando. Integrada e retorno PR entram só uma vez. Confira se o destinatário está
              ativo.
            </li>
            <li>
              <strong>Botão Sair sumiu?</strong> A sidebar fixa o rodapé; role a lista de menus se
              necessário.
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
