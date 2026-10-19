import { useEffect, useState } from "react";

import { getTeachers } from "../api/teachers";
import TeacherPhoto from "../components/TeacherPhoto";
import TeacherAverage from "../components/TeacherAverage";

import "./TeachersPage.css";

function TeacherResults({
  search,
  page,
  onPageChange,
  onRetry,
  onSessionExpired,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    getTeachers(search, page, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result);
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
            requestError.message ||
              "Не удалось загрузить преподавателей.",
          );
        }
      });

    return () => controller.abort();
  }, [search, page, onSessionExpired]);

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

  if (!data) {
    return <p role="status">Загружаем преподавателей…</p>;
  }

  if (!data.results.length) {
    return (
      <p className="teachers-empty" role="status">
        {search
          ? "По этому запросу преподаватели не найдены."
          : "Список преподавателей пока пуст."}
      </p>
    );
  }

  return (
    <>
      <p className="profile-note" role="status">
        {search ? "Найдено" : "Всего преподавателей"}:{" "}
        {data.count}
      </p>

      <div className="teachers-grid">
        {data.results.map((teacher) => (
          <article className="teacher-card" key={teacher.id}>
            <div className="teacher-card-heading">
              <TeacherPhoto
                key={`${teacher.id}-${teacher.photo_updated_at || "empty"}`}
                teacher={teacher}
                onSessionExpired={onSessionExpired}
              />

              <div className="teacher-name">
                <h2>
                  {teacher.full_name || teacher.display_name}
                </h2>

                {teacher.full_name &&
                  teacher.full_name !== teacher.display_name && (
                    <p>{teacher.display_name}</p>
                  )}
              </div>
            </div>
            <TeacherAverage statistics={teacher.grade_statistics} />

            <div className="teacher-subjects">
              <h3>Предметы в сохранённых журналах</h3>

              {teacher.subjects.length ? (
                <details>
                  <summary>
                    Показать предметы ({teacher.subjects.length})
                  </summary>

                  <ul>
                    {teacher.subjects.map((subject) => (
                      <li key={subject}>{subject}</li>
                    ))}
                  </ul>
                </details>
              ) : (
                <p>Предметы пока не указаны.</p>
              )}
            </div>
            <a
              className="teacher-details-link"
              href={`/teachers/${teacher.id}`}
            >
              Подробнее →
            </a>
          </article>
        ))}
      </div>

      <nav
        className="teachers-pagination"
        aria-label="Страницы списка преподавателей"
      >
        <button
          type="button"
          className="portal-action"
          disabled={!data.previous}
          onClick={() => onPageChange(page - 1)}
        >
          Назад
        </button>

        <span>Страница {page}</span>

        <button
          type="button"
          className="portal-action"
          disabled={!data.next}
          onClick={() => onPageChange(page + 1)}
        >
          Далее
        </button>
      </nav>
    </>
  );
}

export default function TeachersPage({ onSessionExpired }) {
  const [input, setInput] = useState("");

  const [query, setQuery] = useState({
    search: "",
    page: 1,
    revision: 0,
  });

  function handleSearch(event) {
    event.preventDefault();

    setQuery((current) => ({
      search: input.trim(),
      page: 1,
      revision: current.revision + 1,
    }));
  }

  function resetSearch() {
    setInput("");

    setQuery((current) => ({
      search: "",
      page: 1,
      revision: current.revision + 1,
    }));
  }

  return (
    <section className="teachers-page">
      <h1>Преподаватели</h1>

      <p className="profile-note">
        Преподаватели из загруженных журналов студентов Altyn.
        Список пополняется при обновлении журналов.
      </p>

      <form
        className="teachers-search"
        onSubmit={handleSearch}
      >
        <div>
          <label htmlFor="teacher-search">
            Фамилия или полное имя
          </label>

          <input
            id="teacher-search"
            type="search"
            value={input}
            maxLength={100}
            placeholder="Например, Садвакасова"
            onChange={(event) => setInput(event.target.value)}
          />
        </div>

        <button type="submit" className="portal-action">
          Найти
        </button>

        {(input || query.search) && (
          <button
            type="button"
            className="portal-action"
            onClick={resetSearch}
          >
            Сбросить
          </button>
        )}
      </form>

      <TeacherResults
        key={JSON.stringify(query)}
        search={query.search}
        page={query.page}
        onSessionExpired={onSessionExpired}
        onPageChange={(page) => {
          setQuery((current) => ({
            ...current,
            page,
          }));
        }}
        onRetry={() => {
          setQuery((current) => ({
            ...current,
            revision: current.revision + 1,
          }));
        }}
      />
    </section>
  );
}