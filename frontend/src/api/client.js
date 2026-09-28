const TOKEN_KEY = "altyn_access";

export function getAccessToken() {
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

export function logoutAltyn() {
  sessionStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event("altyn:logout"));
}

async function request(
  path,
  {
    method = "GET",
    body,
    auth = false,
    signal,
    binary = false,
  } = {},
) {
  const token = auth ? getAccessToken() : "";

  const headers = {
    Accept: binary ? "*/*" : "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(`/api/accounts/${path}`, {
      method,
      headers,
      signal,
      credentials: "omit",
      cache: "no-store",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    throw new Error(
      "Нет соединения с сервером Altyn. Попробуйте позже.",
    );
  }

  if (
    auth &&
    response.status === 401 &&
    getAccessToken() === token
  ) {
    logoutAltyn();
  }

  if (binary && response.ok) {
    return response.blob();
  }

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error(
      "Сервер вернул неожиданный ответ. Попробуйте позже.",
    );
  }

  if (!response.ok) {
    const fields = Object.values(data || {})
      .filter(Array.isArray)
      .flat()
      .filter((value) => typeof value === "string");

    const error = new Error(
      response.status === 429
        ? "Слишком много попыток. Повторите позже."
        : data.message ||
            data.detail ||
            fields.join(" ") ||
            "Запрос не выполнен.",
    );

    error.status = response.status;
    throw error;
  }

  return data;
}

export const checkBackend = () => request("health/");

export async function loginAltyn(iin, password) {
  const data = await request("login/", {
    method: "POST",
    body: { iin, password },
  });

  if (typeof data.access !== "string" || !data.access) {
    throw new Error("Сервер не вернул подтверждение входа.");
  }

  sessionStorage.setItem(TOKEN_KEY, data.access);
}

export async function verifyPlatonus(iin, password, consent) {
  const data = await request("platonus/verify/", {
    method: "POST",
    body: {
      iin,
      platonus_password: password,
      save_platonus_credentials: consent,
    },
  });

  if (
    data.status !== "student_verified" ||
    typeof data.registration_token !== "string" ||
    !/^[A-Za-z0-9_-]{43}$/.test(data.registration_token)
  ) {
    throw new Error("Подтверждение студента не получено.");
  }

  return data;
}

export async function completeRegistration(
  token,
  password,
  passwordConfirm,
) {
  const data = await request("register/complete/", {
    method: "POST",
    body: {
      registration_token: token,
      password,
      password_confirm: passwordConfirm,
    },
  });

  if (data.status !== "registered") {
    throw new Error("Создание аккаунта не подтверждено.");
  }

  return data;
}

export const getProfile = (signal) =>
  request("profile/", {
    auth: true,
    signal,
  });

export const syncProfile = () =>
  request("profile/sync/", {
    method: "POST",
    auth: true,
  });

export const getPhoto = (signal) =>
  request("profile/photo/", {
    auth: true,
    binary: true,
    signal,
  });