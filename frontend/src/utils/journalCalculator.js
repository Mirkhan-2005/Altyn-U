export const COMMON = new Set([
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

const INPUTS = new Set([
  "РК1",
  "РК2",
  "Итоговый контроль",
]);

const SCHEMES = {
  "L,Lab,P,SRO": {
    L: 20,
    Lab: 30,
    P: 20,
    SRO: 30,
  },
  "L,Lab,SRO": {
    L: 20,
    Lab: 50,
    SRO: 30,
  },
  "L,P,SRO": {
    L: 20,
    P: 50,
    SRO: 30,
  },
  "P,SRO": {
    P: 70,
    SRO: 30,
  },
};

export const text = (value) =>
  value == null ? "" : String(value).trim();

export const empty = (value) => text(value) === "";

export const week = (column) =>
  /^(?:[1-9]|1[0-5])$/.test(column);

export const cellKey = (subject, row, column) =>
  JSON.stringify([subject, row, column]);

export const display = (value) =>
  value == null
    ? ""
    : value.toLocaleString("ru-RU", {
        maximumFractionDigits: 2,
      });

export function mark(value, weekly = true) {
  const raw = text(value)
    .toLowerCase()
    .replace(/\s/g, "");

  if (!raw) return { kind: "blank" };

  if (weekly && raw === "н.п.") {
    return { kind: "skip" };
  }

  if (weekly && raw === "н") {
    return { kind: "number", value: 0 };
  }

  if (/^\d{1,3}(?:[.,]\d{1,2})?$/.test(raw)) {
    const number = Number(raw.replace(",", "."));

    if (number <= 100) {
      return { kind: "number", value: number };
    }
  }

  return { kind: "invalid" };
}

export function calculate(
  subject,
  subjectIndex,
  columns,
  edits,
) {
  const rows = subject.rows;

  const types = rows
    .map((row) =>
      /-(Lab|SRO|L|P)$/i
        .exec(text(row["Учебный поток"]))?.[1]
        .toLowerCase(),
    )
    .map(
      (type) =>
        ({
          l: "L",
          lab: "Lab",
          p: "P",
          sro: "SRO",
        })[type],
    );

  const weights = SCHEMES[
    [...types].sort().join(",")
  ];

  const required = [
    "РК1",
    "РК2",
    "Итоговый контроль",
    ...Array.from(
      { length: 15 },
      (_, index) => String(index + 1),
    ),
  ];

  const conflict = columns.some(
    (column) =>
      COMMON.has(column) &&
      rows.some(
        (row) =>
          text(row[column]) !==
          text(rows[0]?.[column]),
      ),
  );

  if (
    !weights ||
    new Set(types).size !== rows.length ||
    conflict ||
    required.some(
      (column) => !columns.includes(column),
    )
  ) {
    return {
      supported: false,
      reason:
        "Для этой дисциплины схема пока не определена. " +
        "Показаны исходные оценки.",
    };
  }

  const key = (row, column) =>
    cellKey(
      subjectIndex,
      COMMON.has(column) ? 0 : row,
      column,
    );

  const hasOverride = (row, column) =>
    Object.hasOwn(edits, key(row, column));
    
  const changed = (row, column) =>
    hasOverride(row, column) &&
    text(edits[key(row, column)]) !==
      text(rows[row][column]);

  // Предположения применяются только к пустым ячейкам.

  const value = (row, column) =>
    hasOverride(row, column)
      ? edits[key(row, column)]
      : rows[row][column];


  const editable = (row, column) =>
    week(column) || INPUTS.has(column);

  const saved = (column) => {
    const result = mark(rows[0][column], false);

    return result.kind === "number"
      ? result.value
      : null;
  };

  const calculated = new Map();

  let invalid = 0;
  let missing = 0;

  function phase(part) {
    const weeks = Array.from(
      { length: part === 1 ? 7 : 8 },
      (_, index) =>
        String(index + (part === 1 ? 1 : 8)),
    );

    let weeklyChanged = false;
    let complete = true;

    const means = rows.map((row, rowIndex) => {
      const marks = weeks.map((column) =>
        mark(value(rowIndex, column)),
      );

      const numbers = marks.filter(
        (item) => item.kind === "number",
      );

      const blanks = marks.filter(
        (item) => item.kind === "blank",
      ).length;

      const errors = marks.filter(
        (item) => item.kind === "invalid",
      ).length;

      missing += blanks;
      invalid += errors;

      complete =
        complete &&
        blanks === 0 &&
        errors === 0 &&
        numbers.length > 0;

      weeklyChanged ||= weeks.some(
        (column) => changed(rowIndex, column),
      );

      // Пустые поля и «н.п.» не входят в среднее.
      // При пустых полях результат предварительный.
      // Все недели, кроме явно обозначенных «н.п.».
      // Пустая неделя входит в знаменатель
      // и даёт 0 баллов в сценарии.
      const activeWeeks = marks.filter(
        (item) => item.kind !== "skip",
      ).length;

      const sum = numbers.reduce(
        (total, item) => total + item.value,
        0,
      );

      const mean =
        activeWeeks > 0 && errors === 0
          ? sum / activeWeeks
          : null;

      calculated.set(
        key(rowIndex, `ТК${part}`),
        mean,
      );

      return mean;
    });

    // Вес отсутствующего вида занятий не перераспределяем.
    let total = means.every(
      (mean) => mean !== null,
    )
      ? means.reduce(
          (sum, mean, index) =>
            sum +
            (mean * weights[types[index]]) / 100,
          0,
        )
      : null;

    if (
      !weeklyChanged &&
      total !== null &&
      saved(`ТК${part} ОБЩ.`) !== null
    ) {
      total = saved(`ТК${part} ОБЩ.`);
    }

    calculated.set(
      key(0, `ТК${part} ОБЩ.`),
      total,
    );

    const control = mark(
      value(0, `РК${part}`),
      false,
    );

    missing += Number(control.kind === "blank");
    invalid += Number(control.kind === "invalid");

    const edited =
      weeklyChanged || changed(0, `РК${part}`);

    let rating =
      total !== null && control.kind === "number"
        ? (total + control.value) / 2
        : null;

    complete =
      complete && control.kind === "number";

    // Сохраняем уже выставленный Р1/Р2,
    // пока исходные данные этой части не изменены.
    if (
      !edited &&
      control.kind === "number" &&
      saved(`Р${part}`) !== null
    ) {
      rating = saved(`Р${part}`);
      complete = true;
    }

    calculated.set(key(0, `Р${part}`), rating);

    return { rating, edited, complete };
  }

  const first = phase(1);
  const second = phase(2);

  const exam = mark(
    value(0, "Итоговый контроль"),
    false,
  );

  invalid += Number(exam.kind === "invalid");
  missing += Number(exam.kind === "blank");

  const edited =
    first.edited ||
    second.edited ||
    changed(0, "Итоговый контроль");

  let admission =
    first.rating !== null &&
    second.rating !== null
      ? (first.rating + second.rating) / 2
      : null;

  if (
    !first.edited &&
    !second.edited &&
    saved("Рейтинг допуска") !== null &&
    first.complete &&
    second.complete
  ) {
    admission = saved("Рейтинг допуска");
  }

  let final =
    admission !== null &&
    exam.kind === "number"
      ? admission * 0.6 + exam.value * 0.4
      : null;


  const official =
    !edited &&
    first.complete &&
    second.complete &&
    exam.kind === "number" &&
    saved("Итоговая оценка / %") !== null;

  if (official) {
    final = saved("Итоговая оценка / %");
  }

  if (invalid) {
    final = null;
  }

  calculated.set(
    key(0, "Рейтинг допуска"),
    admission,
  );

  calculated.set(
    key(0, "Итоговая оценка / %"),
    final,
  );

  return {
    supported: true,
    types,
    weights,
    key,
    value,
    editable,
    calculated,
    final,
    official,
    invalid,
    missing,
    complete:
      official ||
      (
        first.complete &&
        second.complete &&
        exam.kind === "number"
      ),
    // Буквенные оценки сценария добавим
    // после проверки правил перевода.
    letter: official
      ? text(rows[0]["Итоговая оценка / Буквенная"])
      : "",
  };
}