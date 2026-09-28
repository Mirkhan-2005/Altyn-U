import { useEffect, useRef, useState } from "react";

import { getJournal, syncJournal } from "../api/journal";

import "./JournalPage.css";

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString("ru-RU")
    : "Ещё не обновлялось";
}

function JournalTable({ data }) {
  const columns = data.columns.slice(1);

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
          {data.subjects.map((subject, subjectIndex) =>
            subject.rows.map((row, rowIndex) => (
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
                    rowSpan={subject.rows.length}
                  >
                    {subject.name}
                  </th>
                )}

                {columns.map((column) => {
                  const value = row[column];

                  const empty =
                    value === null ||
                    value === undefined ||
                    value === "";

                  const unplanned =
                    String(value)
                      .toLowerCase()
                      .replace(/\s/g, "") === "н.п.";

                  return (
                    <td
                      key={column}
                      className={
                        unplanned
                          ? "journal-unplanned"
                          : undefined
                      }
                    >
                      {empty ? "" : String(value)}
                    </td>
                  );
                })}
              </tr>
            )),
          )}
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
    revision: 0,
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

  const changed =
    Number(year) !== period.year ||
    Number(term) !== period.term;

  useEffect(() => {
    const controller = new AbortController();
    controllerRef.current = controller;

    getJournal(period.year, period.term, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;

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
        } else {
          setMessage(
            error.status === 404
              ? "За этот период журнал ещё не сохранён. Нажмите «Обновить из Platonus»."
              : error.message,
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [period, onSessionExpired]);

  function showPeriod(event) {
    event.preventDefault();

    if (busy) return;

    const nextYear = Number(year);
    const nextTerm = Number(term);

    if (
      !Number.isInteger(nextYear) ||
      nextYear < 2000 ||
      nextYear > 2100 ||
      !Number.isInteger(nextTerm) ||
      nextTerm === 0 ||
      Math.abs(nextTerm) > 20
    ) {
      setMessage("Проверьте учебный год и период.");
      return;
    }

    setSnapshot(null);
    setMessage("");
    setLoading(true);

    setPeriod((current) => ({
      year: nextYear,
      term: nextTerm,
      revision: current.revision + 1,
    }));
  }

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

      if (controller.signal.aborted) return;

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
          `Обновление не выполнено. ${error.message}`,
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

      <form
        onSubmit={showPeriod}
        className="journal-filters"
      >
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

        <button
          type="submit"
          className="portal-action"
          disabled={busy}
        >
          Показать
        </button>
      </form>

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

      {changed && (
        <p className="profile-note">
          Нажмите «Показать», чтобы открыть выбранный период.
        </p>
      )}

      <div role="status" aria-live="polite">
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
          {
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
                <strong>{formatDate(snapshot.last_synced_at)}</strong>
            </div>
          </div> }

          <JournalTable data={snapshot.data} />

          <p className="profile-note">
            Пустые ячейки и обозначения «н» и «н.п.» отображаются
            как в Platonus. При ошибке обновления здесь остаются
            последние сохранённые оценки.
          </p>
        </>
      ) : (
        !loading && (
          <p className="profile-note">
            Сохранённых оценок за этот период пока нет.
          </p>
        )
      )}
    </section>
  );
}