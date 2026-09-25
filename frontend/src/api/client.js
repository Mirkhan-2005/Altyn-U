export async function checkBackend() {
  const response = await fetch("/api/accounts/health/");

  if (!response.ok) {
    throw new Error("Не удалось проверить backend.");
  }

  return response.json();
}

async function postJson(url, payload) {
  let response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(
      "Нет соединения с сервером Altyn. Попробуйте позже.",
    );
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
    const fieldErrors = Object.values(data)
      .filter(Array.isArray)
      .flat()
      .filter((value) => typeof value === "string");

    const message =
      data.message ||
      (response.status === 429
        ? "Слишком много попыток. Подождите немного."
        : null) ||
      data.detail ||
      fieldErrors.join(" ") ||
      "Не удалось выполнить запрос.";

    const error = new Error(message);
    error.status = response.status;

    throw error;
  }

  return data;
}

export async function verifyPlatonus(iin, password, consent) {
  const data = await postJson("/api/accounts/platonus/verify/", {
    iin,
    platonus_password: password,
    save_platonus_credentials: consent,
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
  const data = await postJson("/api/accounts/register/complete/", {
    registration_token: token,
    password,
    password_confirm: passwordConfirm,
  });

  if (data.status !== "registered") {
    throw new Error("Создание аккаунта не подтверждено.");
  }

  return data;
}