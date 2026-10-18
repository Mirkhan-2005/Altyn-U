import { useEffect, useState } from "react";

import { getTeacher } from "../api/teachers";
import TeacherPhoto from "../components/TeacherPhoto";

import "./TeachersPage.css";
import "./TeacherDetailPage.css";

function formatPeriod(year, term) {
  const period =
    term < 0
      ? `дополнительный период ${Math.abs(term)}`
      : `период ${term}`;

  return `${year}–${year + 1}, ${period}`;
}

function getSourceUrl(value) {
  if (!value) return "";

  try {
    const url = new URL(value);

    return ["https:", "http:"].includes(url.protocol)
      ? url.href
      : "";
  } catch {
    return "";
  }
}

function TeacherDetails({
  teacherId,
  onSessionExpired,
  onRetry,
}) {
  const [teacher, setTeacher] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    getTeacher(teacherId, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setTeacher(data);
        }
      })
      .catch((requestError) => {
        if (
          controller.signal.aborted ||
          requestError.name === "AbortError"
        ) {
          return;
        }

        if (requestError.status === 401) {
          onSessionExpired();
        } else {
          setError(
            requestError.status === 404
              ? "Преподаватель не найден."
              : requestError.message ||
                  "Не удалось загрузить преподавателя.",
          );
        }
      });

    return () => controller.abort();
  }, [teacherId, onSessionExpired]);

  if (error) {
    return (
      <div role="alert">
        <p className="portal-message">{error}</p>

        <button
          type="button"
          className="portal-action"
          onClick={onRetry}
        >
          Повторить загрузку
        </button>
      </div>
    );
  }

  if (!teacher) {
    return (
      <p role="status">
        Загружаем информацию о преподавателе…
      </p>
    );
  }

  const name = teacher.full_name || teacher.display_name;
  const sourceUrl = getSourceUrl(teacher.photo_source_url);
  const teaching = teacher.teaching || [];

  return (
    <>
      <section className="teacher-detail-header">
        <TeacherPhoto
          key={`${teacher.id}-${teacher.photo_updated_at || "empty"}`}
          teacher={teacher}
          onSessionExpired={onSessionExpired}
        />

        <div className="teacher-detail-intro">
          <p className="teacher-detail-label">
            ПРЕПОДАВАТЕЛЬ
          </p>

          <h1>{name}</h1>

          {teacher.full_name ? (
            <p className="profile-note">
              Подпись в журнале: {teacher.display_name}
            </p>
          ) : (
            <p className="profile-note">
              Имя показано так, как оно указано в журнале.
            </p>
          )}

          <p>Предметов в сохранённых журналах: {teaching.length}</p>

          {sourceUrl && (
            <a
              className="teacher-source-link"
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Источник фотографии ↗
            </a>
          )}
        </div>
      </section>

      <section
        className="teacher-detail-subjects"
        aria-labelledby="teacher-subjects-title"
      >
        <h2 id="teacher-subjects-title">
          Предметы и учебные периоды
        </h2>

        <p className="profile-note">
          По журналам, загруженным студентами Altyn.
          Список может не включать все предметы преподавателя.
        </p>

        {teaching.length ? (
          <div className="teacher-subject-list">
            {teaching.map((item) => (
              <article
                className="teacher-subject-item"
                key={item.subject}
              >
                <h3>{item.subject}</h3>

                <ul className="teacher-periods">
                  {item.periods.map(({ year, term }) => (
                    <li key={`${year}-${term}`}>
                      {formatPeriod(year, term)}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        ) : (
          <p>Связанные предметы пока не найдены.</p>
        )}
      </section>
    </>
  );
}

export default function TeacherDetailPage({
  teacherId,
  onNavigate,
  onSessionExpired,
}) {
  const [attempt, setAttempt] = useState(0);

  return (
    <div className="teacher-detail-page">
      <button
        type="button"
        className="teacher-back"
        onClick={() => onNavigate("teachers")}
      >
        ← Все преподаватели
      </button>

      <TeacherDetails
        key={`${teacherId}-${attempt}`}
        teacherId={teacherId}
        onSessionExpired={onSessionExpired}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    </div>
  );
}