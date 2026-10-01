import { useEffect, useState } from "react";

import { getProfile } from "../api/client";

import { watchProfile } from "../api/watchProfile";

export default function HomePage({
  onNavigate,
  onSessionExpired,
}) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);




  useEffect(() => {
    return watchProfile(
      (data) => {
        setProfile(data);
        setLoading(false);
        setMessage(data.sync_message || "");
      },
      (error) => {
        setLoading(false);

        if (error.status === 401) {
          onSessionExpired();
        } else {
          setMessage(
            error.message || "Не удалось загрузить профиль.",
          );
        }
      },
    );
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
        {profile?.sync_status === "queued" && (
          <p>Готовим загрузку профиля из Platonus…</p>
        )}

        {profile?.sync_status === "syncing" && (
          <p>Загружаем имя, фамилию, GPA и фотографию…</p>
        )}
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