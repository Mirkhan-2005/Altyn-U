import { useEffect, useState } from "react";
import { verifyPlatonus } from "./api/client";
import "./App.css";

function getCurrentPage() {
  return window.location.pathname === "/register" ? "register" : "login";
}

function AuthForm({ page, onNavigate }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [iin, setIin] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");

  const isRegister = page === "register";

  async function handleSubmit(event) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    setMessage("");

    if (!/^[0-9]{12}$/.test(iin)) {
      setMessage("Введите ИИН из 12 цифр.");
      return;
    }

    if (!password) {
      setMessage(
        isRegister ? "Введите пароль Platonus." : "Введите пароль Altyn.",
      );
      return;
    }

    if (!isRegister) {
      setMessage("Вход в аккаунт Altyn подключим следующим шагом.");
      return;
    }

    setIsSubmitting(true);
    setShowPassword(false);
    setMessage("Проверяем данные в Platonus…");

    try {
      const result = await verifyPlatonus(iin, password);

      setMessage(result.message);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Не удалось выполнить проверку. Попробуйте позже.",
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

        <h1>{isRegister ? "Регистрация" : "С возвращением!"}</h1>

        <p>
          {isRegister
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
            disabled={isSubmitting}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">
            {isRegister ? "Пароль Platonus" : "Пароль Altyn"}
          </label>

          <div className="password-field">
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder={
                isRegister
                  ? "Введите пароль от Platonus"
                  : "Введите пароль от Altyn"
              }
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setMessage("");
              }}
              maxLength={isRegister ? 256 : 128}
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

        {isRegister && (
          <p className="registration-hint">
            Для регистрации необходимо подтвердить роль студента и статус
            обучения «Обучается» в Platonus.
          </p>
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
            ? "Проверяем…"
            : isRegister
              ? "Регистрация"
              : "Войти"}
        </button>
      </form>

      <div className="auth-divider">
        <span>{isRegister ? "Уже есть аккаунт?" : "Ещё нет аккаунта?"}</span>
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

  useEffect(() => {
    function handlePopState() {
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

  function navigate(nextPage) {
    if (nextPage === page) {
      return;
    }

    window.history.pushState({}, "", `/${nextPage}`);
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
        <AuthForm key={page} page={page} onNavigate={navigate} />

        <footer className="page-footer">Altyn · ЕНУ</footer>
      </div>
    </main>
  );
}