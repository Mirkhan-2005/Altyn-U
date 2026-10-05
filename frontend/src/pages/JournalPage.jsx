import { useEffect, useState } from "react";

import useJournal from "../hooks/useJournal";

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
  // null означает: открыть текущий период из настроек backend.
  const [period, setPeriod] = useState(null);
  const [filters, setFilters] = useState(null);

  const {
    snapshot,
    loading,
    syncing,
    message,
    refresh,
    recheck,
  } = useJournal(period, onSessionExpired);

  const year =
    filters?.year ?? String(snapshot?.year ?? "");

  const term =
    filters?.term ?? String(snapshot?.term ?? "");

  const validYear =
    /^[0-9]{4}$/.test(year) &&
    Number(year) >= 2000 &&
    Number(year) <= 2100;

  const validPeriod =
    validYear &&
    Number.isInteger(Number(term)) &&
    Number(term) !== 0 &&
    Math.abs(Number(term)) <= 20;

  const selected =
    period ??
    (snapshot
      ? { year: snapshot.year, term: snapshot.term }
      : null);

  const changed =
    !selected ||
    !validPeriod ||
    Number(year) !== selected.year ||
    Number(term) !== selected.term;

  const busy = loading || syncing;

  const visible =
    snapshot &&
    selected &&
    snapshot.year === selected.year &&
    snapshot.term === selected.term
      ? snapshot
      : null;

  const options = visible?.data?.available_terms?.length
    ? visible.data.available_terms
    : [
        { value: "1", label: "1" },
        { value: "2", label: "2" },
        { value: "-1", label: "Дополнительный 1" },
        { value: "-2", label: "Дополнительный 2" },
      ];

  useEffect(() => {
    if (!filters || !validPeriod || syncing) return;

    const nextYear = Number(filters.year);
    const nextTerm = Number(filters.term);

    if (
      period?.year === nextYear &&
      period?.term === nextTerm
    ) {
      return;
    }

    const timer = setTimeout(() => {
      setPeriod({
        year: nextYear,
        term: nextTerm,
      });
    }, 400);

    return () => clearTimeout(timer);
  }, [filters, validPeriod, syncing, period]);

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
            value={year}
            disabled={busy || !selected}
            aria-invalid={Boolean(year) && !validYear}
            onChange={(event) =>
              setFilters({
                year: event.target.value,
                term,
              })
            }
          />
        </label>

        <label htmlFor="journal-term">
          Академический период

          <select
            id="journal-term"
            value={term}
            disabled={busy || !selected}
            onChange={(event) =>
              setFilters({
                year,
                term: event.target.value,
              })
            }
          >
            {!term && (
              <option value="">Загрузка…</option>
            )}

            {term &&
              !options.some(
                (option) => String(option.value) === term,
              ) && (
                <option value={term}>{term}</option>
              )}

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

      {year && !validYear && (
        <p className="profile-note">
          Введите год от 2000 до 2100.
        </p>
      )}

      <div className="journal-toolbar">
        <p>
          {selected
            ? `Открыт ${selected.year}–${selected.year + 1}, период ${selected.term}`
            : "Определяем текущий период…"}
        </p>

        <button
          type="button"
          className="portal-action"
          disabled={busy || changed || !visible}
          onClick={refresh}
        >
          {syncing
            ? "Обновляем…"
            : "Обновить из Platonus"}
        </button>
      </div>

      <div role="status" aria-live="polite">
        {loading && (
          <p>Загружаем сохранённый журнал…</p>
        )}

        {visible?.refresh_pending && (
          <p>
            Журнал обновляется в фоне.
            Пока показаны сохранённые данные.
          </p>
        )}

        {message && (
          <p className="portal-message">{message}</p>
        )}

        {visible?.auto_message && (
          <p className="portal-message">
            {visible.auto_message}
          </p>
        )}

        {visible?.sync_message &&
          visible.sync_message !== message && (
            <p className="portal-message">
              {visible.sync_message}
            </p>
          )}
      </div>

      {!busy && (
        <button
          type="button"
          className="portal-action"
          disabled={Boolean(selected) && changed}
          onClick={recheck}
        >
          Проверить состояние
        </button>
      )}

      {visible?.has_data ? (
        <>
          <div className="journal-stats">
            <div className="journal-stat">
              <span>Дисциплины</span>
              <strong>
                {visible.data.subjects_count}
              </strong>
            </div>

            <div className="journal-stat">
              <span>Строки занятий</span>
              <strong>
                {visible.data.rows_count}
              </strong>
            </div>

            <div className="journal-stat journal-stat-date">
              <span>
                Последнее успешное обновление
              </span>

              <strong>
                {formatDate(visible.last_synced_at)}
              </strong>
            </div>
          </div>

          {visible.data.is_empty === true ? (
            <p className="portal-message">
              На момент последней проверки за этот
              период нет дисциплин и оценок.
            </p>
          ) : (
            <JournalTable data={visible.data} />
          )}

          <p className="profile-note">
            При недоступности Platonus последние
            сохранённые оценки остаются здесь.
          </p>
        </>
      ) : (
        !loading && (
          <p className="profile-note">
            Журнал за этот период пока не сохранён.
          </p>
        )
      )}
    </section>
  );
}