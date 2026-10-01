import { useEffect, useRef, useState } from "react";

import { syncProfile } from "../api/client";
import { watchProfile } from "../api/watchProfile";
import StudentPhoto from "../components/StudentPhoto";

function formatDate(value) {
  if (!value) return "Ещё не обновлялось";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Дата неизвестна"
    : date.toLocaleString("ru-RU");
}

export default function ProfilePage({ onSessionExpired }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);

  const mounted = useRef(false);

  const profileUpdating =
    profile?.sync_status === "queued" ||
    profile?.sync_status === "syncing";

  const busy = loading || syncing || profileUpdating;

  useEffect(() => {
    mounted.current = true;

    const stop = watchProfile(
      (data) => {
        setProfile(data);
        setLoading(false);
        setMessage("");
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

    return () => {
      mounted.current = false;
      stop();
    };
  }, [attempt, onSessionExpired]);

  async function handleSync() {
    if (busy) return;

    setSyncing(true);
    setMessage("Отправляем запрос на обновление профиля…");

    try {
      const data = await syncProfile();

      if (!mounted.current) return;

      setProfile(data);
      setMessage("");
      setAttempt((value) => value + 1);
    } catch (error) {
      if (!mounted.current) return;

      if (error.status === 401) {
        onSessionExpired();
      } else {
        setMessage(
          error.message || "Не удалось обновить профиль.",
        );
      }
    } finally {
      if (mounted.current) {
        setSyncing(false);
      }
    }
  }

  function retryLoading() {
    setLoading(true);
    setMessage("");
    setAttempt((value) => value + 1);
  }

  return (
    <>
      <h1>Мой профиль</h1>

      <div role="status" aria-live="polite">
        {message && (
          <p className="portal-message">{message}</p>
        )}

        {profile?.sync_status === "queued" && (
          <p>Обновление профиля ожидает выполнения…</p>
        )}

        {profile?.sync_status === "syncing" && (
          <p>Получаем данные из Platonus…</p>
        )}

        {profile?.sync_message &&
          profile.sync_message !== message && (
            <p className="portal-message">
              {profile.sync_message}
            </p>
          )}
      </div>

      {loading && (
        <p>
          {profile
            ? "Проверяем состояние профиля…"
            : "Загружаем сохранённый профиль…"}
        </p>
      )}

      {message && !loading && !syncing && (
        <button
          type="button"
          className="portal-action"
          onClick={retryLoading}
        >
          Повторить загрузку профиля
        </button>
      )}

      {profile && (
        <section className="profile-card">
          {profile.photo_url ? (
            <StudentPhoto
              key={profile.photo_updated_at || profile.photo_url}
              onSessionExpired={onSessionExpired}
            />
          ) : (
            <div className="student-photo photo-placeholder">
              {profileUpdating ? "Загружаем фото…" : "Нет фото"}
            </div>
          )}

          <div className="profile-details">
            <dl>
              <div>
                <dt>Имя</dt>
                <dd>
                  {profile.first_name || "Пока не загружено"}
                </dd>
              </div>

              <div>
                <dt>Фамилия</dt>
                <dd>
                  {profile.last_name || "Пока не загружена"}
                </dd>
              </div>

              <div>
                <dt>GPA из Platonus</dt>
                <dd className="gpa-value">
                  {profile.gpa ?? "—"}
                </dd>
              </div>
            </dl>

            <p>
              Профиль обновлён:{" "}
              {formatDate(profile.last_synced_at)}
            </p>

            <p>
              GPA обновлён:{" "}
              {formatDate(profile.gpa_updated_at)}
            </p>

            <p>
              Фото обновлено:{" "}
              {formatDate(profile.photo_updated_at)}
            </p>

            {profile.sync_status === "pending" && (
              <p>
                Нажми «Обновить из Platonus», чтобы заполнить
                профиль.
              </p>
            )}

            <button
              type="button"
              className="portal-action"
              disabled={busy}
              onClick={handleSync}
            >
              {syncing
                ? "Отправляем запрос…"
                : profile.sync_status === "queued"
                  ? "Ожидаем обновления…"
                  : profile.sync_status === "syncing"
                    ? "Обновляем профиль…"
                    : "Обновить из Platonus"}
            </button>

            <p className="profile-note">
              При недоступности Platonus здесь остаются
              последние сохранённые данные.
            </p>
          </div>
        </section>
      )}
    </>
  );
}