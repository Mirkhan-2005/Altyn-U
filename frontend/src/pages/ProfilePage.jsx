import { useEffect, useRef, useState } from "react";

import { getProfile, syncProfile } from "../api/client";
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

  useEffect(() => {
    mounted.current = true;

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
      mounted.current = false;
      controller.abort();
    };
  }, [attempt, onSessionExpired]);

  async function handleSync() {
    if (loading || syncing) return;

    setSyncing(true);
    setMessage("Обновляем данные из Platonus…");

    try {
      const data = await syncProfile();

      if (!mounted.current) return;

      setProfile(data);
      setMessage(data.sync_message || "Профиль обновлён.");
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
      </div>

      {loading && !profile && (
        <p>Загружаем сохранённый профиль…</p>
      )}

      {!profile && !loading && (
        <button
          type="button"
          className="portal-action"
          onClick={retryLoading}
        >
          Повторить загрузку
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
              Нет фото
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

            {profile.sync_message && (
              <p className="portal-message">
                {profile.sync_message}
              </p>
            )}

            <button
              type="button"
              className="portal-action"
              disabled={syncing}
              onClick={handleSync}
            >
              {syncing ? "Обновляем…" : "Обновить из Platonus"}
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