import { useEffect, useRef, useState } from "react";

import { getJournal, syncJournal } from "../api/journal";

import "./JournalPage.css";

function formatDate(value) {
  if (!value) {
    return "Ещё не обновлялось";
  }

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Дата недоступна"
    : date.toLocaleString("ru-RU");
}

function JournalTable({ data }) {
  const columns = data.columns.slice(1);

  // Общие показатели дисциплины:
  // объединяем их по вертикали, если значения совпадают.
  const subjectColumns = new Set([
    "ТК1 ОБЩ.",
    "РК1",
    "Р1",
    "ТК2 ОБЩ.",
    "РК2",
    "Р2",
    "Оценка за курсовую работу",
    "Практика",
    "Исследоват. работа",
    "Рейтинг допуска",
    "Итоговый контроль",
    "Итоговая оценка / %",
    "Итоговая оценка / Буквенная",
  ]);

  function cellText(value) {
    return value === null || value === undefined
      ? ""
      : String(value);
  }

  return (
    <div
      className="journal-scroll"
      tabIndex={0}
      role="region"
      aria-label="Таблица оценок с горизонтальной прокруткой"
    >
      <table className="journal-table">
        <caption>
          {data.academic_year}, академический период {data.term}
        </caption>

        <thead>
          <tr>
            {data.columns.map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {data.subjects.map((subject, subjectIndex) => {
            const rows = subject.rows;

            if (!rows.length) {
              return null;
            }

            const mergedColumns = new Set(
              columns.filter((column) => {
                if (!subjectColumns.has(column)) {
                  return false;
                }

                const firstValue = cellText(rows[0][column]);

                return rows.every(
                  (row) => cellText(row[column]) === firstValue,
                );
              }),
            );

            return rows.map((row, rowIndex) => (
              <tr
                key={`${subjectIndex}-${rowIndex}`}
                className={
                  rowIndex === 0
                    ? "journal-subject-start"
                    : undefined
                }
              >
                {rowIndex === 0 && (
                  <th
                    className="journal-subject"
                    rowSpan={rows.length}
                  >
                    {subject.name}
                  </th>
                )}

                {columns.map((column) => {
                  const merged = mergedColumns.has(column);

                  // Ячейка уже показана в первой строке
                  // и занимает высоту всех строк дисциплины.
                  if (merged && rowIndex > 0) {
                    return null;
                  }

                  const text = cellText(row[column]);

                  const unplanned =
                    text.toLowerCase().replace(/\s/g, "") === "н.п.";

                  const className = [
                    merged ? "journal-merged" : "",
                    unplanned ? "journal-unplanned" : "",
                  ]
                    .filter(Boolean)
                    .join(" ");

                  return (
                    <td
                      key={column}
                      rowSpan={merged ? rows.length : undefined}
                      className={className || undefined}
                    >
                      {text}
                    </td>
                  );
                })}
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function JournalPage({ onSessionExpired }) {
  const [year, setYear] = useState("2025");
  const [term, setTerm] = useState("2");

  const [period, setPeriod] = useState({
    year: 2025,
    term: 2,
  });

  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  const [options, setOptions] = useState([
    { value: "1", label: "1" },
    { value: "2", label: "2" },
  ]);

  const controllerRef = useRef(null);

  const busy = loading || syncing;

  const validYear =
    /^[0-9]{4}$/.test(year) &&
    Number(year) >= 2000 &&
    Number(year) <= 2100;

  const validTerm =
    Number.isInteger(Number(term)) &&
    Number(term) !== 0 &&
    Math.abs(Number(term)) <= 20;

  const validPeriod = validYear && validTerm;

  const changed =
    !validPeriod ||
    Number(year) !== period.year ||
    Number(term) !== period.term;

  // Загружаем сохранённый журнал из БД.
  useEffect(() => {
    const controller = new AbortController();

    controllerRef.current = controller;

    getJournal(period.year, period.term, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) {
          return;
        }

        setSnapshot(data);

        if (data.data?.available_terms?.length) {
          setOptions(data.data.available_terms);
        }
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

        setMessage(
          error.status === 404
            ? "За этот период журнал ещё не сохранён. Нажмите «Обновить из Platonus»."
            : error.message || "Не удалось загрузить журнал.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [period, onSessionExpired]);

  // Автоматически переключаем период после изменения фильтров.
  useEffect(() => {
    if (!validPeriod || syncing) {
      return;
    }

    const nextYear = Number(year);
    const nextTerm = Number(term);

    if (
      nextYear === period.year &&
      nextTerm === period.term
    ) {
      return;
    }

    const timer = window.setTimeout(() => {
      setSnapshot(null);
      setMessage("");
      setLoading(true);

      setPeriod({
        year: nextYear,
        term: nextTerm,
      });
    }, 400);

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    year,
    term,
    validPeriod,
    syncing,
    period.year,
    period.term,
  ]);

  // Свежие данные из Platonus получаем только по кнопке.
  async function refreshJournal() {
    const controller = controllerRef.current;

    if (
      busy ||
      changed ||
      !controller ||
      controller.signal.aborted
    ) {
      return;
    }

    setSyncing(true);
    setMessage("Получаем свежий журнал из Platonus…");

    try {
      const data = await syncJournal(
        period.year,
        period.term,
        controller.signal,
      );

      if (controller.signal.aborted) {
        return;
      }

      setSnapshot(data);

      if (data.data?.available_terms?.length) {
        setOptions(data.data.available_terms);
      }

      setMessage(data.sync_message || "Журнал обновлён.");
    } catch (error) {
      if (
        controller.signal.aborted ||
        error.name === "AbortError"
      ) {
        return;
      }

      if (error.status === 401) {
        onSessionExpired();
      } else {
        setMessage(
          `Обновление не выполнено. ${
            error.message || "Попробуйте позже."
          }`,
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setSyncing(false);
      }
    }
  }

  return (
    <section className="journal-page">
      <h1>Мой журнал</h1>

      <div className="journal-filters">
        <label htmlFor="journal-year">
          Начало учебного года

          <input
            id="journal-year"
            type="number"
            min="2000"
            max="2100"
            step="1"
            required
            value={year}
            disabled={busy}
            aria-invalid={!validYear}
            aria-describedby={
              !validYear ? "journal-year-error" : undefined
            }
            onChange={(event) => setYear(event.target.value)}
          />
        </label>

        <label htmlFor="journal-term">
          Академический период

          <select
            id="journal-term"
            value={term}
            disabled={busy}
            onChange={(event) => setTerm(event.target.value)}
          >
            {options.map((option) => (
              <option
                key={option.value}
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!validYear && (
        <p id="journal-year-error" className="profile-note">
          Введите год из четырёх цифр: от 2000 до 2100.
        </p>
      )}

      <div className="journal-toolbar">
        <p>
          Открыт {period.year}–{period.year + 1},
          период {period.term}
        </p>

        <button
          type="button"
          className="portal-action"
          disabled={busy || changed}
          onClick={refreshJournal}
        >
          {syncing ? "Обновляем…" : "Обновить из Platonus"}
        </button>
      </div>

      <div role="status" aria-live="polite">
        {changed && validPeriod && !busy && (
          <p className="profile-note">
            Открываем выбранный период…
          </p>
        )}

        {loading && (
          <p>Загружаем сохранённый журнал…</p>
        )}

        {message && (
          <p className="portal-message">{message}</p>
        )}
      </div>

      {snapshot?.sync_message &&
        snapshot.sync_message !== message && (
          <p className="portal-message">
            {snapshot.sync_message}
          </p>
        )}

      {snapshot?.has_data ? (
        <>
          <div className="journal-stats">
            <div className="journal-stat">
              <span>Дисциплины</span>
              <strong>{snapshot.data.subjects_count}</strong>
            </div>

            <div className="journal-stat">
              <span>Строки занятий</span>
              <strong>{snapshot.data.rows_count}</strong>
            </div>

            <div className="journal-stat journal-stat-date">
              <span>Последнее успешное обновление</span>
              <strong>
                {formatDate(snapshot.last_synced_at)}
              </strong>
            </div>
          </div>

          <JournalTable data={snapshot.data} />

          <p className="profile-note">
            Пустые ячейки и обозначения «н» и «н.п.» отображаются
            как в Platonus. При ошибке обновления здесь остаются
            последние сохранённые оценки.
          </p>
        </>
      ) : (
        !loading &&
        !message && (
          <p className="profile-note">
            Сохранённых оценок за этот период пока нет.
          </p>
        )
      )}
    </section>
  );
}