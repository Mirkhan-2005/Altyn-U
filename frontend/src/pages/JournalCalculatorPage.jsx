import { useState } from "react";

import useJournal from "../hooks/useJournal";

import {
  COMMON,
  calculate,
  cellKey,
  display,
  empty,
  mark,
  text,
  week,
} from "../utils/journalCalculator";

import "./JournalPage.css";
import "./JournalCalculatorPage.css";

function Calculator({ snapshot }) {
  const [scenario, setScenario] = useState({
    base: null,
    edits: {},
  });

  const base = scenario.base ?? snapshot;
  const { columns, subjects } = base.data;

  const changed =
    Object.keys(scenario.edits).length > 0;

  const newer =
    scenario.base &&
    (
      base.last_synced_at !== snapshot.last_synced_at ||
      base.year !== snapshot.year ||
      base.term !== snapshot.term
    );

  const results = subjects.map((subject, index) =>
    calculate(
      subject,
      index,
      columns,
      scenario.edits,
    ),
  );


  function edit(key, value, originalValue) {
    setScenario((previous) => {
      const edits = { ...previous.edits };

      // Вернули исходное значение — убираем предположение.
      if (text(value) === text(originalValue)) {
        delete edits[key];
      } else {
        edits[key] = value;
      }

      return {
        base: Object.keys(edits).length
          ? (previous.base ?? snapshot)
          : null,
        edits,
      };
    });
  }


  function reset() {
    if (
      changed &&
      !window.confirm(
        "Сбросить предполагаемые оценки?",
      )
    ) {
      return;
    }

    setScenario({
      base: null,
      edits: {},
    });
  }

  return (
    <>
      <div className="journal-toolbar">
        <p>
          {base.year}–{base.year + 1},
          период {base.term}
        </p>

        <button
          type="button"
          className="portal-action"
          disabled={!changed}
          onClick={reset}
        >
          Сбросить сценарий
        </button>
      </div>

      <p className="profile-note">
        Данные на{" "}
        {base.last_synced_at
          ? new Date(
              base.last_synced_at,
            ).toLocaleString("ru-RU")
          : "неизвестную дату"}.
        {" "}Введённые оценки хранятся только на этой
        странице и исчезнут при выходе из неё.
      </p>

      {newer && (
        <p className="portal-message" role="status">
          Получен более свежий журнал. Ваш сценарий
          сохранён на прежних данных. Нажмите
          «Сбросить сценарий», чтобы начать расчёт
          по свежим оценкам.
        </p>
      )}

      <div className="calculator-results">
        {subjects.map((subject, index) => {
          const result = results[index];

          return (
            <article
              className="calculator-result"
              key={index}
            >
              <h2>{subject.name}</h2>

              {result.supported ? (
                <>
                  <span>
                    {result.official
                      ? "Итог из Platonus"
                      : "Расчётный итог"}
                  </span>

                  <strong>
                    {result.final === null
                      ? "Нет расчёта"
                      : `${
                          result.official ? "" : "≈ "
                        }${display(result.final)}`}
                  </strong>

                  <p>
                    {result.invalid
                      ? "Исправьте выделенные поля."
                      : result.final === null
                        ? "Добавьте недостающие оценки и экзамен."
                        : !result.complete
                          ? "Предварительно: заполнены не все поля."
                          : result.official
                            ? "Оценка уже выставлена."
                            : "Все данные для сценария заданы."}
                  </p>

                  <small>
                    {Object.entries(result.weights)
                      .map(
                        ([type, weight]) =>
                          `${type}: ${weight}%`,
                      )
                      .join(" · ")}
                  </small>
                </>
              ) : (
                <p>{result.reason}</p>
              )}
            </article>
          );
        })}
      </div>

      <datalist id="calculator-marks">
        <option value="н.п." />
        <option value="н" />
      </datalist>

      <div
        className="journal-scroll"
        tabIndex={0}
        role="region"
        aria-label="Журнал-калькулятор с горизонтальной прокруткой"
      >
        <table className="journal-table calculator-table">
          <caption>
            Жёлтые поля — ваши предположения.
            Зелёные ячейки — расчёт.
          </caption>

          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {subjects.map((subject, subjectIndex) => {
              const result = results[subjectIndex];

              const merged = new Set(
                columns.filter(
                  (column) =>
                    COMMON.has(column) &&
                    subject.rows.every(
                      (row) =>
                        text(row[column]) ===
                        text(
                          subject.rows[0]?.[column],
                        ),
                    ),
                ),
              );

              return subject.rows.map(
                (row, rowIndex) => (
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

                    {columns.slice(1).map((column) => {
                      const shared =
                        merged.has(column);

                      if (shared && rowIndex > 0) {
                        return null;
                      }

                      const key = cellKey(
                        subjectIndex,
                        shared ? 0 : rowIndex,
                        column,
                      );

                      const overridden =
                        Object.hasOwn(
                        scenario.edits,
                        key,
                        );

                      const editable =
                        result.supported &&
                        result.editable(
                          rowIndex,
                          column,
                        );

                      const calculated =
                        result.supported &&
                        result.calculated.has(key);

                      const value = result.supported
                        ? result.value(
                            rowIndex,
                            column,
                          )
                        : row[column];

                      const invalid =
                        editable &&
                        mark(
                          value,
                          week(column),
                        ).kind === "invalid";

                      const className = [
                        shared
                          ? "journal-merged"
                          : "",
                        editable
                          ? "calculator-editable"
                          : "",
                        calculated
                          ? "calculator-derived"
                          : "",
                        mark(value).kind === "skip"
                          ? "journal-unplanned"
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" ");

                      return (
                        <td
                          key={column}
                          rowSpan={
                            shared
                              ? subject.rows.length
                              : undefined
                          }
                          className={className}
                        >
                          {editable ? (
                            <div className="calculator-input-wrap">
                              <input
                                type="text"
                                inputMode="decimal"
                                maxLength={8}
                                autoComplete="off"
                                value={value}
                                list={
                                  week(column)
                                    ? "calculator-marks"
                                    : undefined
                                }
                                aria-label={
                                  `${subject.name}, ` +
                                  `${text(row["Учебный поток"])}, ` +
                                  column
                                }
                                aria-invalid={invalid}
                                data-overridden={overridden}
                                title={
                                  "Исходное значение: " +
                                  (text(row[column]) || "пусто")
                                }
                                onChange={(event) =>
                                  edit(
                                    key,
                                    event.target.value,
                                    row[column],
                                  )
                                }
                              />

                              {overridden && (
                                <button
                                  type="button"
                                  className="calculator-restore"
                                  title="Вернуть исходную оценку"
                                  aria-label={
                                    `Вернуть исходную оценку: ` +
                                    `${subject.name}, ${column}`
                                  }
                                  onClick={() =>
                                    edit(
                                      key,
                                      text(row[column]),
                                      row[column],
                                    )
                                  }
                                >
                                  Было:{" "}
                                  {text(row[column]) || "пусто"}
                                  {" "}↶
                                </button>
                              )}

                              {invalid && (
                                <small className="calculator-field-error">
                                  {week(column)
                                    ? "Введите 0–100, н или н.п."
                                    : "Введите число 0–100"}
                                </small>
                              )}
                            </div>
                          ) : calculated ? (
                            <span
                              title={
                                "Расчёт сценария. В Platonus: " +
                                (text(row[column]) || "пусто")
                              }
                            >
                              {display(
                                result.calculated.get(key),
                              )}
                            </span>
                          ) : (
                            column ===
                              "Итоговая оценка / Буквенная" &&
                            result.supported
                          ) ? (
                            result.letter
                          ) : (
                            text(value)
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ),
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="profile-note">
        Пустые поля не считаются нулями; среднее
        по заполненным полям предварительное.
        «н» и 0 учитываются как ноль, «н.п.»
        исключается из среднего. В пустой неделе
        можно предположить «н.п.», если занятия
        не будет.
      </p>

      <p className="profile-note">
        Р1/Р2 = (общий ТК + РК) / 2;
        рейтинг допуска = (Р1 + Р2) / 2;
        итог = рейтинг допуска × 0,6 +
        экзамен × 0,4.
        Прогноз показывается до двух знаков,
        без промежуточного округления.
        Правила округления Platonus и условия допуска
        могут изменить официальный итог.
        Буквенная оценка и право на стипендию
        в этой версии не прогнозируются.
      </p>
    </>
  );
}

export default function JournalCalculatorPage({
  onSessionExpired,
}) {
  const {
    snapshot,
    loading,
    syncing,
    message,
    refresh,
    recheck,
  } = useJournal(null, onSessionExpired);

  const busy =
    loading ||
    syncing ||
    Boolean(snapshot?.refresh_pending);

  return (
    <section className="journal-page calculator-page">
      <h1>Журнал-калькулятор</h1>

      <p className="profile-note">
        Измени оценки текущего периода и посмотри
        возможный результат. Можно менять как пустые,
        так и уже заполненные оценки.
        Изменения действуют только в сценарии:
        исходный журнал Altyn и Platonus сохраняется.
      </p>

      <div className="calculator-actions">
        <button
          type="button"
          className="portal-action"
          disabled={busy || !snapshot}
          onClick={refresh}
        >
          {syncing
            ? "Обновляем…"
            : "Обновить из Platonus"}
        </button>

        <button
          type="button"
          className="portal-action"
          disabled={loading || syncing}
          onClick={recheck}
        >
          Проверить состояние
        </button>
      </div>

      <div role="status" aria-live="polite">
        {loading && (
          <p>Загружаем текущий журнал…</p>
        )}

        {snapshot?.refresh_pending && (
          <p>Свежие оценки загружаются в фоне…</p>
        )}

        {[
          ...new Set([
            message,
            snapshot?.auto_message,
            snapshot?.sync_message,
          ]),
        ]
          .filter(Boolean)
          .map((item) => (
            <p
              key={item}
              className="portal-message"
            >
              {item}
            </p>
          ))}
      </div>

      {snapshot?.has_data &&
      snapshot.data.subjects.length > 0 ? (
        <Calculator snapshot={snapshot} />
      ) : (
        !loading && (
          <p>
            Журнал текущего периода пока пуст
            или ещё не загружен.
          </p>
        )
      )}
    </section>
  );
}