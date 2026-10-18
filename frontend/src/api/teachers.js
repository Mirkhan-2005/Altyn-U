import { getAccessToken } from "./client";

async function teacherRequest(path, signal, binary = false) {
  const token = getAccessToken();

  if (!token) {
    const error = new Error("Войдите в аккаунт Altyn.");
    error.status = 401;
    throw error;
  }

  let response;

  try {
    response = await fetch(`/api/teachers/${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: binary ? "*/*" : "application/json",
      },
      signal,
      credentials: "omit",
      cache: "no-store",
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    throw new Error("Нет соединения с сервером Altyn.");
  }

  if (!response.ok) {
    const error = new Error(
      response.status === 401
        ? "Сессия истекла. Войдите снова."
        : response.status === 404
          ? "Запрашиваемые данные не найдены."
          : "Не удалось загрузить данные преподавателей.",
    );

    error.status = response.status;
    throw error;
  }

  if (binary) {
    return response.blob();
  }

  return response.json();
}

export function getTeachers(search, page, signal) {
  const params = new URLSearchParams({
    search,
    page: String(page),
  });

  return teacherRequest(`?${params}`, signal);
}

export function getTeacherPhoto(teacherId, signal) {
  return teacherRequest(
    `${teacherId}/photo/`,
    signal,
    true,
  );
}

export function getTeacher(teacherId, signal) {
  return teacherRequest(`${teacherId}/`, signal);
}