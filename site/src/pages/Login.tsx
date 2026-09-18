import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { BrandLogo } from "../components/BrandLogo";
import { useAuth } from "../auth";

type Mode = "login" | "forgot" | "reset";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login");
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgot = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMensagem(null);
    setSubmitting(true);
    try {
      const result = await api<{ mensagem: string }>("/auth/forgot-password", {
        method: "POST",
        body: { email },
        auth: false,
      });
      setMensagem(result.mensagem);
      setMode("reset");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao solicitar codigo");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMensagem(null);
    setSubmitting(true);
    try {
      const result = await api<{ mensagem: string }>("/auth/reset-password", {
        method: "POST",
        body: { email, code, new_password: newPassword },
        auth: false,
      });
      setMensagem(result.mensagem);
      setMode("login");
      setPassword("");
      setCode("");
      setNewPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao redefinir senha");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-wrap">
      <form
        className="login-card"
        onSubmit={mode === "login" ? handleLogin : mode === "forgot" ? handleForgot : handleReset}
      >
        <BrandLogo compact />
        <p className="subtitle">
          {mode === "login" && "Acesso ao painel de integração de notas fiscais"}
          {mode === "forgot" && "Informe o e-mail cadastrado para receber o código"}
          {mode === "reset" && "Digite o código recebido e a nova senha"}
        </p>

        {mode === "login" && (
          <>
            <label>
              Usuário
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </label>
            <label>
              Senha
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
          </>
        )}

        {mode !== "login" && (
          <label>
            E-mail
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus={mode === "forgot"}
            />
          </label>
        )}

        {mode === "reset" && (
          <>
            <label>
              Código
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                inputMode="numeric"
              />
            </label>
            <label>
              Nova senha
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={4}
              />
            </label>
          </>
        )}

        {mensagem && <div className="alert-success">{mensagem}</div>}
        {error && <div className="alert-error">{error}</div>}

        <button className="btn-primary" type="submit" disabled={submitting}>
          {submitting
            ? "Aguarde..."
            : mode === "login"
              ? "Entrar"
              : mode === "forgot"
                ? "Enviar código"
                : "Salvar nova senha"}
        </button>

        <div className="login-links">
          {mode === "login" ? (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setMode("forgot");
                setError(null);
                setMensagem(null);
              }}
            >
              Esqueci minha senha
            </button>
          ) : (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setMode("login");
                setError(null);
                setMensagem(null);
              }}
            >
              Voltar ao login
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
