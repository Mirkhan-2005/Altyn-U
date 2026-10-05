import { getAccessToken } from "./client";

async function journalRequest(
  url,
  { method = "GET", body, signal } = {},
) {
  const token = getAccessToken();

  if (!token) {
    throw Object.assign(
      new Error("Войдите в Altyn заново."),
      { status: 401 },
    );
  }

  let response;

  try {
    response = await fetch(url, {
      method,
      signal,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;

    throw new Error("Нет соединения с сервером Altyn.");
  }

  let data;

  try {
    data = await response.json();
  } catch (error) {
    if (error.name === "AbortError") throw error;

    throw Object.assign(
      new Error("Сервер вернул неожиданный ответ."),
      { status: response.status },
    );
  }

  if (!response.ok) {
    const fields =
      data && typeof data === "object"
        ? Object.values(data)
            .filter(Array.isArray)
            .flat()
            .filter((value) => typeof value === "string")
            .join(" ")
        : "";

    const message =
      response.status === 429
        ? "Слишком много обновлений. Попробуйте позже."
        : data?.detail ||
          data?.message ||
          fields ||
          "Не удалось получить журнал.";

    throw Object.assign(
      new Error(message),
      { status: response.status },
    );
  }

  return data;
}

function validateJournal(data, year, term) {
  if (
    !data ||
    data.year !== year ||
    data.term !== term ||
    typeof data.has_data !== "boolean" ||
    (
      data.has_data &&
      (
        !Array.isArray(data.data?.columns) ||
        data.data.columns[0] !== "Дисциплина" ||
        !Array.isArray(data.data.subjects) ||
        !data.data.subjects.every(
          (subject) => Array.isArray(subject.rows),
        )
      )
    )
  ) {
    throw new Error(
      "Сервер вернул неожиданный формат журнала.",
    );
  }

  return data;
}

export async function getJournal(year, term, signal) {
  const query = new URLSearchParams({ year, term });

  const data = await journalRequest(
    `/api/journal/?${query}`,
    { signal },
  );

  return validateJournal(data, year, term);
}

export async function syncJournal(year, term, signal) {
  const data = await journalRequest(
    "/api/journal/sync/",
    {
      method: "POST",
      body: { year, term },
      signal,
    },
  );

  return validateJournal(data, year, term);
}



export async function getJournalState(year, term, signal) {
  const query =
    year == null || term == null
      ? ""
      : `?${new URLSearchParams({ year, term })}`;

  const data = await journalRequest(
    `/api/journal/auto-sync/${query}`,
    { signal },
  );

  return validateJournal(
    data,
    year ?? data.year,
    term ?? data.term,
  );
}

export async function autoSyncJournal(year, term, signal) {
  const data = await journalRequest(
    "/api/journal/auto-sync/",
    {
      method: "POST",
      body: { year, term },
      signal,
    },
  );

  return validateJournal(data, year, term);
}