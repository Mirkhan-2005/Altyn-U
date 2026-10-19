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
        Средний балл
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
        Только завершённые ТК · все периоды
      </span>
    </div>
  );
}