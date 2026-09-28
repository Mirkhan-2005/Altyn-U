import { useState } from "react";

import {
  verifyPlatonus,
  completeRegistration,
  loginAltyn,
} from "../api/client";

import PasswordField from "../components/PasswordField";

export default function RegisterPage({
  onNavigate,
  onAuthenticated,
}) {
  const [iin, setIin] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [consent, setConsent] = useState(false);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const passwordStep = Boolean(token);

  async function handleSubmit(event) {
    event.preventDefault();

    if (busy) return;

    if (!/^[0-9]{12}$/.test(iin) || !password) {
      setMessage("Введите ИИН из 12 цифр и пароль.");
      return;
    }

    if (!passwordStep && !consent) {
      setMessage(
        "Подтвердите согласие на сохранение подключения.",
      );
      return;
    }

    if (passwordStep && password !== confirm) {
      setMessage("Пароли не совпадают.");
      return;
    }

    setBusy(true);
    setMessage(
      passwordStep
        ? "Создаём аккаунт…"
        : "Проверяем Platonus…",
    );

    try {
      if (!passwordStep) {
        const result = await verifyPlatonus(
          iin,
          password,
          consent,
        );

        setToken(result.registration_token);

        setMessage(
          "Студент подтверждён. Создайте пароль Altyn в течение 10 минут.",
        );
      } else {
        await completeRegistration(
          token,
          password,
          confirm,
        );

        setToken("");

        // Аккаунт уже создан, даже если последующий вход не удастся.
        try {
          await loginAltyn(iin, password);
          onAuthenticated();
        } catch {
          onNavigate(
            "login",
            "Аккаунт создан. Войдите с новым паролем Altyn.",
          );
        }
      }
    } catch (error) {
      if (error.status === 410) {
        setToken("");
        setConsent(false);
      }

      setMessage(
        error.message || "Не удалось завершить регистрацию.",
      );
    } finally {
      setPassword("");
      setConfirm("");
      setBusy(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-heading">
        <span className="auth-label">
          СОЗДАНИЕ АККАУНТА
        </span>

        <h1>
          {passwordStep ? "Создай пароль" : "Регистрация"}
        </h1>

        <p>
          {passwordStep
            ? "Придумай отдельный пароль для входа в Altyn."
            : "Подтверди через Platonus, что ты студент ЕНУ."}
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-busy={busy}>
        <div className="form-field">
          <label htmlFor="register-iin">ИИН</label>

          <input
            id="register-iin"
            name="username"
            type="text"
            inputMode="numeric"
            autoComplete="username"
            pattern="[0-9]{12}"
            placeholder="Введите 12 цифр"
            maxLength={12}
            required
            value={iin}
            readOnly={passwordStep}
            disabled={busy}
            onChange={(event) =>
              setIin(
                event.target.value.replace(/\D/g, "").slice(0, 12),
              )
            }
          />
        </div>

        <PasswordField
          key={passwordStep ? "altyn" : "platonus"}
          id="register-password"
          label={
            passwordStep
              ? "Новый пароль Altyn"
              : "Пароль Platonus"
          }
          autoComplete={
            passwordStep ? "new-password" : "current-password"
          }
          value={password}
          minLength={passwordStep ? 8 : undefined}
          maxLength={passwordStep ? 128 : 256}
          disabled={busy}
          onChange={(event) => setPassword(event.target.value)}
        />

        {passwordStep ? (
          <>
            <PasswordField
              id="password-confirm"
              label="Повторите пароль Altyn"
              autoComplete="new-password"
              value={confirm}
              minLength={8}
              maxLength={128}
              disabled={busy}
              onChange={(event) => setConfirm(event.target.value)}
            />

            <p className="registration-hint">
              Минимум 8 символов. Не повторяй пароль Platonus.
            </p>
          </>
        ) : (
          <>
            <p className="registration-hint">
              Проверим роль «Студент» и статус «Обучается».
            </p>

            <label className="consent-field">
              <input
                type="checkbox"
                required
                checked={consent}
                disabled={busy}
                onChange={(event) =>
                  setConsent(event.target.checked)
                }
              />

              <span>
                Согласен на сохранение ИИН и зашифрованного
                пароля Platonus для подключения и обновления
                учебных данных.
              </span>
            </label>
          </>
        )}

        <div role="status" aria-live="polite">
          {message && (
            <p className="form-message">{message}</p>
          )}
        </div>

        <button
          className="button button-primary"
          disabled={busy}
        >
          {busy
            ? "Подождите…"
            : passwordStep
              ? "Создать аккаунт"
              : "Регистрация"}
        </button>
      </form>

      <div className="auth-divider">
        <span>Уже есть аккаунт?</span>
      </div>

      <button
        className="button button-secondary"
        disabled={busy}
        onClick={() => onNavigate("login")}
      >
        Войти
      </button>
    </section>
  );
}