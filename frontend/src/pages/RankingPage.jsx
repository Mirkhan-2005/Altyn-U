import { useEffect, useState } from "react";
import { getStudentRanking } from "../api/client";
import "./RankingPage.css";

function formatDate(value) {
  if (!value) return "Дата не указана";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Дата не указана"
    : date.toLocaleDateString("ru-RU");
}

export default function RankingPage({ onSessionExpired }) {
  const [query, setQuery] = useState({
    course: "",
    program: "",
    page: 1,
    revision: 0,
  });

  const [filters, setFilters] = useState({
    courses: [],
    programs: [],
  });

  const [response, setResponse] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    getStudentRanking(query, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;

        setFilters(data.available_filters);
        setResponse({ query, data, error: "" });
      })
      .catch((error) => {
        if (
          controller.signal.aborted ||
          error.name === "AbortError"
        ) {
          return;
        }

        if (error.status === 401) {
          onSessionExpired();
          return;
        }

        setResponse({
          query,
          data: null,
          error: error.message || "Не удалось загрузить рейтинг.",
        });
      });

    return () => controller.abort();
  }, [query, onSessionExpired]);

  // Ответ от предыдущих фильтров не показываем как новый.
  const ready = response?.query === query;
  const data = ready ? response.data : null;
  const error = ready ? response.error : "";
  const loading = !ready;

  function changeFilter(name, value) {
    setQuery((current) => ({
      ...current,
      [name]: value,
      page: 1,
    }));
  }

  function reload() {
    setQuery((current) => ({
      ...current,
      page: 1,
      revision: current.revision + 1,
    }));
  }

  return (
    <section className="ranking-page">
      <header className="ranking-heading">
        <span className="ranking-eyebrow">УСПЕВАЕМОСТЬ</span>

        <h1>Рейтинг по GPA</h1>

        <p>
          Среди студентов Altyn с загруженным GPA.
          Выбери курс и программу для сравнения внутри своей группы.
        </p>
      </header>

      <div className="ranking-filters">
        <label>
          <span>Курс</span>

          <select
            value={query.course}
            disabled={loading}
            onChange={(event) =>
              changeFilter("course", event.target.value)
            }
          >
            <option value="">Все курсы</option>

            {filters.courses.map((course) => (
              <option key={course} value={course}>
                {course} курс
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Образовательная программа</span>

          <select
            value={query.program}
            disabled={loading}
            onChange={(event) =>
              changeFilter("program", event.target.value)
            }
          >
            <option value="">Все программы</option>

            {filters.programs.map((program) => (
              <option key={program.code} value={program.code}>
                {program.name} ({program.code})
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="portal-action"
          disabled={loading}
          onClick={reload}
        >
          Обновить список
        </button>

        {(query.course || query.program) && (
          <button
            type="button"
            className="portal-action"
            disabled={loading}
            onClick={() =>
              setQuery((current) => ({
                course: "",
                program: "",
                page: 1,
                revision: current.revision + 1,
              }))
            }
          >
            Сбросить
          </button>
        )}
      </div>

      {loading && <p role="status">Загружаем рейтинг…</p>}

      {error && (
        <div role="alert" className="portal-message">
          <p>{error}</p>

          <button
            type="button"
            className="portal-action"
            onClick={reload}
          >
            Повторить загрузку
          </button>
        </div>
      )}

      {data && (
        <>
          {data.my_result ? (
            <div className="ranking-personal">
              <div>
                <span>Твоё место в выбранном рейтинге</span>
                <strong>№ {data.my_result.rank}</strong>
              </div>

              <div>
                <span>Твой GPA</span>
                <strong>{data.my_result.gpa}</strong>
              </div>

              <div>
                <span>GPA обновлён</span>
                <b>{formatDate(data.my_result.gpa_updated_at)}</b>
              </div>
            </div>
          ) : (
            <p className="profile-note">
              Твоей записи нет в этом рейтинге. Возможно, GPA ещё не
              загружен или твой профиль не входит в выбранную группу.
            </p>
          )}

          <p className="profile-note" role="status">
            Участников: {data.count}. При одинаковом GPA место одинаковое.
          </p>

          {data.results.length === 0 ? (
            <p className="ranking-empty">
              Для выбранных условий пока нет участников.
            </p>
          ) : (
            <>
              <div
                className="ranking-table-wrap"
                role="region"
                aria-label="Рейтинг студентов по GPA"
                tabIndex={0}
              >
                <table className="ranking-table">
                  <thead>
                    <tr>
                      <th scope="col">Место</th>
                      <th scope="col">Студент</th>
                      <th scope="col">Курс</th>
                      <th scope="col">GPA</th>
                      <th scope="col">GPA обновлён</th>
                    </tr>
                  </thead>

                  <tbody>
                    {data.results.map((student) => (
                      <tr
                        key={student.id}
                        className={student.is_me ? "ranking-me" : ""}
                      >
                        <td>
                          <span
                            className="ranking-position"
                            data-top={student.rank <= 3}
                          >
                            {student.rank}
                          </span>
                        </td>

                        <td className="ranking-student">
                          <strong>{student.full_name}</strong>

                          {student.is_me && (
                            <span className="ranking-you">Ты</span>
                          )}

                          <small>
                            {student.education_program ||
                              "Программа не указана"}

                            {student.education_program_code &&
                              ` (${student.education_program_code})`}
                          </small>
                        </td>

                        <td>{student.course ?? "—"}</td>

                        <td className="ranking-gpa">
                          {student.gpa}
                        </td>

                        <td>
                          {formatDate(student.gpa_updated_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <nav
                className="ranking-pagination"
                aria-label="Страницы рейтинга"
              >
                <button
                  type="button"
                  className="portal-action"
                  disabled={data.previous_page === null}
                  onClick={() =>
                    setQuery((current) => ({
                      ...current,
                      page: data.previous_page,
                    }))
                  }
                >
                  Назад
                </button>

                <span>
                  Страница {data.page} из {data.total_pages}
                </span>

                <button
                  type="button"
                  className="portal-action"
                  disabled={data.next_page === null}
                  onClick={() =>
                    setQuery((current) => ({
                      ...current,
                      page: data.next_page,
                    }))
                  }
                >
                  Далее
                </button>
              </nav>
            </>
          )}

          <p className="ranking-footnote">
            Используется последний GPA, сохранённый в Altyn.
            Даты обновления у студентов могут отличаться.
          </p>
        </>
      )}
    </section>
  );
}