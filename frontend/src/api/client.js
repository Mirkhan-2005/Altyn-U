export async function checkBackend() {
  const response = await fetch("/api/accounts/health/", {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(
      `Не удалось проверить backend. HTTP ${response.status}`,
    );
  }

  return response.json();
}

export async function verifyPlatonus(iin, password) {
  let response;

  try {
    response = await fetch("/api/accounts/platonus/verify/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        iin,
        platonus_password: password,
      }),
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
    const message =
      data.message ||
      data.iin?.[0] ||
      data.platonus_password?.[0] ||
      (response.status === 429
        ? "Слишком много попыток. Подождите немного."
        : null) ||
      data.detail ||
      "Не удалось выполнить проверку.";

    throw new Error(message);
  }

  if (data.status !== "student_verified") {
    throw new Error("Подтверждение студента не получено.");
  }

  return data;
}