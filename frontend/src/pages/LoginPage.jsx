import { useState } from "react";

import { loginAltyn } from "../api/client";
import PasswordField from "../components/PasswordField";

export default function LoginPage({
  onNavigate,
  onAuthenticated,
  initialMessage = "",
}) {
  const [iin, setIin] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(initialMessage);

  async function handleSubmit(event) {
    event.preventDefault();

    if (busy) return;

    if (!/^[0-9]{12}$/.test(iin) || !password) {
      setMessage("Введите ИИН из 12 цифр и пароль Altyn.");
      return;
    }

    setBusy(true);
    setMessage("Входим…");

    try {
      await loginAltyn(iin, password);
      onAuthenticated();
    } catch (error) {
      setMessage(error.message || "Не удалось войти.");
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-heading">
        <span className="auth-label">
          ЛИЧНОЕ ПРОСТРАНСТВО
        </span>

        <h1>С возвращением!</h1>

        <p>
          Войди по ИИН и паролю своего аккаунта Altyn.
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-busy={busy}>
        <div className="form-field">
          <label htmlFor="login-iin">ИИН</label>

          <input
            id="login-iin"
            name="username"
            type="text"
            inputMode="numeric"
            autoComplete="username"
            placeholder="Введите 12 цифр"
            pattern="[0-9]{12}"
            maxLength={12}
            required
            disabled={busy}
            value={iin}
            onChange={(event) =>
              setIin(
                event.target.value.replace(/\D/g, "").slice(0, 12),
              )
            }
          />
        </div>

        <PasswordField
          id="login-password"
          label="Пароль Altyn"
          autoComplete="current-password"
          placeholder="Введите пароль Altyn"
          value={password}
          maxLength={128}
          disabled={busy}
          onChange={(event) => setPassword(event.target.value)}
        />

        <div role="status" aria-live="polite">
          {message && (
            <p className="form-message">{message}</p>
          )}
        </div>

        <button
          className="button button-primary"
          disabled={busy}
        >
          {busy ? "Входим…" : "Войти"}
        </button>
      </form>

      <div className="auth-divider">
        <span>Ещё нет аккаунта?</span>
      </div>

      <button
        className="button button-secondary"
        disabled={busy}
        onClick={() => onNavigate("register")}
      >
        Регистрация
      </button>
    </section>
  );
}