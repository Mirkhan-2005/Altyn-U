import { getProfile } from "./client";

export function watchProfile(onData, onError) {
  const controller = new AbortController();

  let stopped = false;
  let timer = null;

  const startedAt = Date.now();

  async function load() {
    try {
      const data = await getProfile(controller.signal);

      if (stopped) return;

      onData(data);

      const waiting =
        data.sync_status === "queued" ||
        data.sync_status === "syncing";

      if (!waiting) return;

      if (Date.now() - startedAt >= 5 * 60 * 1000) {
        onError(
          new Error(
            "Загрузка затянулась. Откройте страницу позже, " +
              "чтобы проверить результат.",
          ),
        );
        return;
      }

      timer = window.setTimeout(load, 2000);
    } catch (error) {
      if (stopped || error.name === "AbortError") return;

      onError(error);
    }
  }

  load();

  return () => {
    stopped = true;
    window.clearTimeout(timer);
    controller.abort();
  };
}