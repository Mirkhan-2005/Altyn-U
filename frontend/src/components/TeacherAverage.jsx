export default function TeacherAverage({ statistics }) {
  const raw = statistics?.average_score;
  const score = raw == null ? null : Number(raw);
  const count = statistics?.students_count ?? 0;

  const available =
    score !== null &&
    Number.isFinite(score) &&
    count > 0;

  return (
    <div className="teacher-average">
      <span className="teacher-average-label">
        Расчётный средний балл
      </span>

      {available ? (
        <>
          <strong className="teacher-average-value">
            {score.toLocaleString("ru-RU", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}

            <span> / 100</span>
          </strong>

          <span className="teacher-average-note">
            Студентов в расчёте: {count}
          </span>
        </>
      ) : (
        <strong className="teacher-average-empty">
          Недостаточно данных
        </strong>
      )}

      <span className="teacher-average-note">
        Прошлые обычные периоды: ТК1/ТК2, а при пустом ТК —
        среднее числовых недельных оценок соответствующего блока.
        Текущий период исключён.
      </span>
    </div>
  );
}