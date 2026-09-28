import { useEffect, useState } from "react";

import { getProfile } from "../api/client";

export default function HomePage({
  onNavigate,
  onSessionExpired,
}) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    getProfile(controller.signal)
      .then((data) => {
        if (active) {
          setProfile(data);
        }
      })
      .catch((error) => {
        if (!active || error.name === "AbortError") return;

        if (error.status === 401) {
          onSessionExpired();
        } else {
          setMessage(
            error.message || "Не удалось загрузить профиль.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [attempt, onSessionExpired]);

  return (
    <>
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
          type="button"
          className="portal-action"
          onClick={() => onNavigate("profile")}
        >
          Открыть профиль
        </button>
      </section>

      <div role="status" aria-live="polite">
        {message && (
          <p className="portal-message">{message}</p>
        )}

        {loading && (
          <p>Загружаем сохранённый профиль…</p>
        )}
      </div>

      {!profile && !loading && (
        <button
          type="button"
          className="portal-action"
          onClick={() => {
            setLoading(true);
            setMessage("");
            setAttempt((value) => value + 1);
          }}
        >
          Повторить загрузку
        </button>
      )}
    </>
  );
}