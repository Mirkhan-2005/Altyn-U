import { useEffect, useState } from "react";
import {
  verifyPlatonus,
  completeRegistration,
} from "./api/client";
import "./App.css";

function getCurrentPage() {
  return window.location.pathname === "/register"
    ? "register"
    : "login";
}

function AuthForm({ page, onNavigate, initialMessage }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [iin, setIin] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState(initialMessage);
  const [consent, setConsent] = useState(false);
  const [registrationToken, setRegistrationToken] = useState("");

  const isRegister = page === "register";
  const isPasswordStep = isRegister && Boolean(registrationToken);

  async function handleSubmit(event) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    setMessage("");

    if (!isRegister) {
      setMessage("Вход в аккаунт Altyn подключим следующим шагом.");
      return;
    }

    if (isPasswordStep) {
      if (password !== passwordConfirm) {
        setMessage("Пароли не совпадают.");
        return;
      }

      setIsSubmitting(true);
      setShowPassword(false);
      setMessage("Создаём аккаунт…");

      try {
        await completeRegistration(
          registrationToken,
          password,
          passwordConfirm,
        );

        setRegistrationToken("");
        setPassword("");
        setPasswordConfirm("");

        onNavigate(
          "login",
          "Аккаунт Altyn создан. Вход подключим следующим шагом.",
        );
      } catch (error) {
        if (error.status === 410) {
          setRegistrationToken("");
          setPassword("");
          setPasswordConfirm("");
          setConsent(false);
        }

        setMessage(
          error instanceof Error
            ? error.message
            : "Не удалось завершить регистрацию.",
        );
      } finally {
        setIsSubmitting(false);
      }

      return;
    }

    if (!/^[0-9]{12}$/.test(iin)) {
      setMessage("Введите ИИН из 12 цифр.");
      return;
    }

    if (!password) {
      setMessage("Введите пароль Platonus.");
      return;
    }

    if (!consent) {
      setMessage("Подтвердите согласие на сохранение подключения.");
      return;
    }

    setIsSubmitting(true);
    setShowPassword(false);
    setMessage("Проверяем данные в Platonus…");

    try {
      const result = await verifyPlatonus(iin, password, consent);

      setRegistrationToken(result.registration_token);
      setPasswordConfirm("");
      setMessage(
        "Студент подтверждён. Создайте пароль Altyn в течение 10 минут.",
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Не удалось выполнить проверку.",
      );
    } finally {
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-heading">
        <span className="auth-label">
          {isRegister ? "СОЗДАНИЕ АККАУНТА" : "ЛИЧНОЕ ПРОСТРАНСТВО"}
        </span>

        <h1>
          {isPasswordStep
            ? "Создай пароль"
            : isRegister
              ? "Регистрация"
              : "С возвращением!"}
        </h1>

        <p>
          {isPasswordStep
            ? "Придумай отдельный пароль для входа в Altyn."
            : isRegister
              ? "Введи данные Platonus, чтобы подтвердить, что ты студент ЕНУ."
              : "Войди по ИИН и паролю своего аккаунта Altyn."}
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-busy={isSubmitting}>
        <div className="form-field">
          <label htmlFor="iin">ИИН</label>

          <input
            id="iin"
            name="username"
            type="text"
            inputMode="numeric"
            autoComplete="username"
            placeholder="Введите 12 цифр"
            value={iin}
            onChange={(event) => {
              setIin(event.target.value.replace(/\D/g, "").slice(0, 12));
              setMessage("");
            }}
            minLength={12}
            maxLength={12}
            pattern="[0-9]{12}"
            title="ИИН должен содержать ровно 12 цифр"
            readOnly={isPasswordStep}
            disabled={isSubmitting}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">
            {isPasswordStep
              ? "Новый пароль Altyn"
              : isRegister
                ? "Пароль Platonus"
                : "Пароль Altyn"}
          </label>

          <div className="password-field">
            <input
              key={isPasswordStep ? "new-password" : "current-password"}
              id="password"
              name={isPasswordStep ? "new-password" : "password"}
              type={showPassword ? "text" : "password"}
              autoComplete={
                isPasswordStep ? "new-password" : "current-password"
              }
              placeholder={
                isPasswordStep
                  ? "Придумайте пароль Altyn"
                  : isRegister
                    ? "Введите пароль от Platonus"
                    : "Введите пароль от Altyn"
              }
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setMessage("");
              }}
              minLength={isPasswordStep ? 8 : undefined}
              maxLength={isRegister && !isPasswordStep ? 256 : 128}
              disabled={isSubmitting}
              required
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword((previous) => !previous)}
              aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
              aria-pressed={showPassword}
              aria-controls="password"
              disabled={isSubmitting}
            >
              {showPassword ? "Скрыть" : "Показать"}
            </button>
          </div>
        </div>

        {isPasswordStep && (
          <>
            <div className="form-field">
              <label htmlFor="password-confirm">
                Повторите пароль Altyn
              </label>

              <input
                id="password-confirm"
                name="password-confirm"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                placeholder="Повторите новый пароль"
                value={passwordConfirm}
                onChange={(event) => {
                  setPasswordConfirm(event.target.value);
                  setMessage("");
                }}
                minLength={8}
                maxLength={128}
                disabled={isSubmitting}
                required
              />
            </div>

            <p className="registration-hint">
              Минимум 8 символов. Используй сочетание букв, цифр и
              символов. Не повторяй пароль Platonus.
            </p>
          </>
        )}

        {isRegister && !isPasswordStep && (
          <>
            <p className="registration-hint">
              Для регистрации необходимо подтвердить роль студента
              и статус обучения «Обучается» в Platonus.
            </p>

            <label className="consent-field">
              <input
                type="checkbox"
                checked={consent}
                onChange={(event) => {
                  setConsent(event.target.checked);
                  setMessage("");
                }}
                disabled={isSubmitting}
                required
              />

              <span>
                Согласен на сохранение ИИН и зашифрованного пароля
                Platonus для подключения и обновления учебных данных.
              </span>
            </label>
          </>
        )}

        <div role="status" aria-live="polite" aria-atomic="true">
          {message && <p className="form-message">{message}</p>}
        </div>

        <button
          type="submit"
          className="button button-primary"
          disabled={isSubmitting}
        >
          {isSubmitting
            ? isPasswordStep
              ? "Создаём аккаунт…"
              : "Проверяем…"
            : isPasswordStep
              ? "Создать аккаунт"
              : isRegister
                ? "Регистрация"
                : "Войти"}
        </button>
      </form>

      <div className="auth-divider">
        <span>
          {isRegister ? "Уже есть аккаунт?" : "Ещё нет аккаунта?"}
        </span>
      </div>

      <button
        type="button"
        className="button button-secondary"
        onClick={() => onNavigate(isRegister ? "login" : "register")}
        disabled={isSubmitting}
      >
        {isRegister ? "Войти" : "Регистрация"}
      </button>
    </section>
  );
}

export default function App() {
  const [page, setPage] = useState(getCurrentPage);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    function handlePopState() {
      setNotice("");
      setPage(getCurrentPage());
    }

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useEffect(() => {
    document.title =
      page === "register" ? "Регистрация — Altyn" : "Вход — Altyn";
  }, [page]);

  function navigate(nextPage, nextNotice = "") {
    if (nextPage === page) {
      return;
    }

    window.history.pushState({}, "", `/${nextPage}`);
    setNotice(nextNotice);
    setPage(nextPage);
  }

  return (
    <main className="auth-layout">
      <aside className="brand-panel">
        <div className="brand">
          altyn<span>.</span>
        </div>

        <div className="brand-content">
          <span className="university-label">ДЛЯ СТУДЕНТОВ ЕНУ</span>

          <h2>
            Твой путь.
            <br />
            Твой <span>результат.</span>
          </h2>

          <p>Твоё студенческое пространство начинается здесь.</p>
        </div>

        <p className="brand-footer">Независимый студенческий проект</p>
      </aside>

      <div className="form-panel">
        <AuthForm
          key={page}
          page={page}
          onNavigate={navigate}
          initialMessage={notice}
        />

        <footer className="page-footer">Altyn · ЕНУ</footer>
      </div>
    </main>
  );
}