import { useEffect, useState } from "react";

import {
  completeRegistration,
  getAccessToken,
  getPhoto,
  getProfile,
  loginAltyn,
  logoutAltyn,
  syncProfile,
  verifyPlatonus,
} from "./api/client";

import "./App.css";

const paths = {
  home: "/",
  profile: "/profile",
  login: "/login",
  register: "/register",
};

function getCurrentPage() {
  return (
    Object.keys(paths).find(
      (key) => paths[key] === window.location.pathname,
    ) || "login"
  );
}

function AuthForm({ page, onNavigate, onLogin, initialMessage }) {
  const [iin, setIin] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [consent, setConsent] = useState(false);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(initialMessage);

  const isRegister = page === "register";
  const passwordStep = isRegister && Boolean(token);

  async function handleSubmit(event) {
    event.preventDefault();

    if (busy) return;

    if (!/^[0-9]{12}$/.test(iin)) {
      setMessage("Введите ИИН из 12 цифр.");
      return;
    }

    if (passwordStep && password !== confirm) {
      setMessage("Пароли не совпадают.");
      return;
    }

    if (isRegister && !passwordStep && !consent) {
      setMessage("Подтвердите согласие на сохранение подключения.");
      return;
    }

    setBusy(true);
    setShow(false);
    setMessage("Подождите…");

    let accountCreated = false;

    try {
      if (!isRegister) {
        await loginAltyn(iin, password);
        onLogin(false);
      } else if (passwordStep) {
        await completeRegistration(token, password, confirm);

        accountCreated = true;
        setToken("");

        await loginAltyn(iin, password);
        onLogin(true);
      } else {
        const result = await verifyPlatonus(iin, password, consent);

        setToken(result.registration_token);
        setMessage(
          "Студент подтверждён. Создайте пароль Altyn в течение 10 минут.",
        );
      }
    } catch (error) {
      if (accountCreated) {
        onNavigate(
          "login",
          "Аккаунт создан. Войдите с новым паролем Altyn. При необходимости обновите профиль кнопкой.",
        );
      } else {
        if (error.status === 410) {
          setToken("");
          setConsent(false);
        }

        setMessage(error.message);
      }
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
          {isRegister ? "СОЗДАНИЕ АККАУНТА" : "ЛИЧНОЕ ПРОСТРАНСТВО"}
        </span>

        <h1>
          {passwordStep
            ? "Создай пароль"
            : isRegister
              ? "Регистрация"
              : "С возвращением!"}
        </h1>

        <p>
          {passwordStep
            ? "Придумай отдельный пароль для Altyn."
            : isRegister
              ? "Подтверди, что ты студент ЕНУ, через Platonus."
              : "Войди по ИИН и паролю своего аккаунта Altyn."}
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-busy={busy}>
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
            onChange={(event) =>
              setIin(event.target.value.replace(/\D/g, "").slice(0, 12))
            }
            pattern="[0-9]{12}"
            minLength={12}
            maxLength={12}
            readOnly={passwordStep}
            disabled={busy}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">
            {passwordStep
              ? "Новый пароль Altyn"
              : isRegister
                ? "Пароль Platonus"
                : "Пароль Altyn"}
          </label>

          <div className="password-field">
            <input
              id="password"
              name="password"
              type={show ? "text" : "password"}
              autoComplete={
                passwordStep ? "new-password" : "current-password"
              }
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={passwordStep ? 8 : undefined}
              maxLength={isRegister && !passwordStep ? 256 : 128}
              disabled={busy}
              required
            />

            <button
              type="button"
              className="password-toggle"
              disabled={busy}
              onClick={() => setShow(!show)}
              aria-pressed={show}
              aria-label={show ? "Скрыть пароль" : "Показать пароль"}
            >
              {show ? "Скрыть" : "Показать"}
            </button>
          </div>
        </div>

        {passwordStep && (
          <div className="form-field">
            <label htmlFor="confirm">Повторите пароль Altyn</label>

            <input
              id="confirm"
              name="password-confirm"
              type={show ? "text" : "password"}
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              minLength={8}
              maxLength={128}
              disabled={busy}
              required
            />

            <p className="registration-hint">
              Минимум 8 символов. Не повторяй пароль Platonus.
            </p>
          </div>
        )}

        {isRegister && !passwordStep && (
          <label className="consent-field">
            <input
              type="checkbox"
              checked={consent}
              disabled={busy}
              required
              onChange={(event) => setConsent(event.target.checked)}
            />

            <span>
              Согласен на сохранение ИИН и зашифрованного пароля
              Platonus для подключения и обновления учебных данных.
            </span>
          </label>
        )}

        <div role="status" aria-live="polite">
          {message && <p className="form-message">{message}</p>}
        </div>

        <button
          type="submit"
          className="button button-primary"
          disabled={busy}
        >
          {busy
            ? "Подождите…"
            : passwordStep
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
        disabled={busy}
        onClick={() => onNavigate(isRegister ? "login" : "register")}
      >
        {isRegister ? "Войти" : "Регистрация"}
      </button>
    </section>
  );
}

function StudentPhoto({ available }) {
  const [src, setSrc] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!available) return;

    const controller = new AbortController();
    let objectUrl;

    getPhoto(controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;

        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setFailed(true);
        }
      });

    return () => {
      controller.abort();

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [available]);

  if (src && !failed) {
    return (
      <img
        className="student-photo"
        src={src}
        alt="Фото студента"
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <div className="student-photo photo-placeholder">
      {failed
        ? "Фото недоступно"
        : available
          ? "Загрузка фото…"
          : "Нет фото"}
    </div>
  );
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString("ru-RU")
    : "Ещё не обновлялось";
}

export default function App() {
  const [page, setPage] = useState(getCurrentPage);
  const [access, setAccess] = useState(getAccessToken);
  const [profile, setProfile] = useState(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [reload, setReload] = useState(0);

  const visiblePage = access
    ? page === "profile"
      ? "profile"
      : "home"
    : page === "register"
      ? "register"
      : "login";

  function navigate(nextPage, message = "") {
    window.history.pushState({}, "", paths[nextPage]);
    setNotice(message);
    setPage(nextPage);
  }

  useEffect(() => {
    function onPop() {
      setPage(getCurrentPage());
      setNotice("");
    }

    function onLogout() {
      setAccess("");
      setProfile(null);
      setSyncing(false);
      setNotice("");

      window.history.replaceState({}, "", paths.login);
      setPage("login");
    }

    window.addEventListener("popstate", onPop);
    window.addEventListener("altyn:logout", onLogout);

    return () => {
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("altyn:logout", onLogout);
    };
  }, []);

  useEffect(() => {
    const titles = {
      home: "Главная",
      profile: "Профиль",
      login: "Вход",
      register: "Регистрация",
    };

    document.title = `${titles[visiblePage]} — Altyn`;

    if (window.location.pathname !== paths[visiblePage]) {
      window.history.replaceState({}, "", paths[visiblePage]);
    }
  }, [visiblePage, page]);

  useEffect(() => {
    if (!access || syncing) return;

    const controller = new AbortController();

    getProfile(controller.signal)
      .then((data) => {
        if (
          !controller.signal.aborted &&
          getAccessToken() === access
        ) {
          setProfile(data);
        }
      })
      .catch((error) => {
        if (
          !controller.signal.aborted &&
          getAccessToken() === access
        ) {
          setNotice(error.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [access, syncing, reload]);

  async function refreshProfile() {
    if (syncing) return;

    const token = getAccessToken();

    setSyncing(true);
    setNotice("Обновляем данные из Platonus…");

    try {
      const data = await syncProfile();

      if (getAccessToken() === token) {
        setProfile(data);
        setNotice(data.sync_message || "Профиль обновлён.");
      }
    } catch (error) {
      if (getAccessToken() === token) {
        setNotice(error.message);
      }
    } finally {
      if (getAccessToken() === token) {
        setSyncing(false);
      }
    }
  }

  function finishLogin(firstSync) {
    setAccess(getAccessToken());
    setProfile(null);
    setLoading(true);

    navigate("home");

    if (firstSync) {
      void refreshProfile();
    }
  }

  if (!access) {
    return (
      <main className="auth-layout">
        <aside className="brand-panel">
          <div className="brand">
            altyn<span>.</span>
          </div>

          <div className="brand-content">
            <span className="university-label">
              ДЛЯ СТУДЕНТОВ ЕНУ
            </span>

            <h2>
              Твой путь.
              <br />
              Твой <span>результат.</span>
            </h2>

            <p>Твоё студенческое пространство начинается здесь.</p>
          </div>

          <p className="brand-footer">
            Независимый студенческий проект
          </p>
        </aside>

        <div className="form-panel">
          <AuthForm
            key={visiblePage}
            page={visiblePage}
            initialMessage={notice}
            onNavigate={navigate}
            onLogin={finishLogin}
          />

          <footer className="page-footer">Altyn · ЕНУ</footer>
        </div>
      </main>
    );
  }

  return (
    <div className="portal">
      <header className="portal-header">
        <button
          className="portal-logo"
          onClick={() => navigate("home")}
        >
          altyn.
        </button>

        <nav aria-label="Главное меню">
          <button
            aria-current={visiblePage === "home" ? "page" : undefined}
            onClick={() => navigate("home")}
          >
            Главная
          </button>

          <button
            aria-current={
              visiblePage === "profile" ? "page" : undefined
            }
            onClick={() => navigate("profile")}
          >
            Профиль
          </button>

          <button onClick={logoutAltyn}>Выйти</button>
        </nav>
      </header>

      <main className="portal-main">
        {visiblePage === "home" ? (
          <section className="welcome-banner">
            <span>ТВОЁ СТУДЕНЧЕСКОЕ ПРОСТРАНСТВО</span>

            <h1>
              Привет
              {profile?.first_name ? `, ${profile.first_name}` : ""}!
            </h1>

            <p>
              Имя, GPA и фотография из Platonus — в твоём профиле.
            </p>

            <button
              className="portal-action"
              onClick={() => navigate("profile")}
            >
              Открыть профиль
            </button>
          </section>
        ) : (
          <h1>Мой профиль</h1>
        )}

        <div role="status" aria-live="polite">
          {notice && <p className="portal-message">{notice}</p>}
        </div>

        {loading && !profile && (
          <p>Загружаем сохранённый профиль…</p>
        )}

        {!profile && !loading && !syncing && (
          <button
            className="portal-action"
            onClick={() => {
              setLoading(true);
              setReload((value) => value + 1);
            }}
          >
            Повторить загрузку
          </button>
        )}

        {visiblePage === "profile" && profile && (
          <section className="profile-card">
            <StudentPhoto
              key={profile.photo_updated_at || "empty"}
              available={Boolean(profile.photo_url)}
            />

            <div className="profile-details">
              <dl>
                <div>
                  <dt>Имя</dt>
                  <dd>{profile.first_name || "Пока не загружено"}</dd>
                </div>

                <div>
                  <dt>Фамилия</dt>
                  <dd>{profile.last_name || "Пока не загружена"}</dd>
                </div>

                <div>
                  <dt>GPA из Platonus</dt>
                  <dd className="gpa-value">{profile.gpa ?? "—"}</dd>
                </div>
              </dl>

              <p>
                Профиль обновлён: {formatDate(profile.last_synced_at)}
              </p>
              <p>
                GPA обновлён: {formatDate(profile.gpa_updated_at)}
              </p>
              <p>
                Фото обновлено: {formatDate(profile.photo_updated_at)}
              </p>

              {profile.sync_status === "pending" && (
                <p>
                  Нажми «Обновить из Platonus», чтобы заполнить профиль.
                </p>
              )}

              {profile.sync_message && (
                <p className="portal-message">
                  {profile.sync_message}
                </p>
              )}

              <button
                className="portal-action"
                disabled={syncing}
                onClick={refreshProfile}
              >
                {syncing ? "Обновляем…" : "Обновить из Platonus"}
              </button>

              <p className="profile-note">
                При недоступности Platonus здесь остаются последние
                сохранённые данные.
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}