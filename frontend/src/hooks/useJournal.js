import { useEffect, useRef, useState } from "react";

import {
  getJournalState,
  autoSyncJournal,
  syncJournal,
} from "../api/journal";

function pause(signal) {
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };

    const timer = setTimeout(finish, 3000);

    signal.addEventListener("abort", finish, {
      once: true,
    });

    if (signal.aborted) finish();
  });
}

export default function useJournal(period, onSessionExpired) {
  const year = period?.year;
  const term = period?.term;

  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");
  const [revision, setRevision] = useState(0);

  const request = useRef(null);
  const manual = useRef(false);
  const lastAutoKey = useRef(null);
  const expired = useRef(onSessionExpired);

  useEffect(() => {
    expired.current = onSessionExpired;
  }, [onSessionExpired]);

  useEffect(() => {
    const controller = new AbortController();
    request.current = controller;

    const { signal } = controller;

    const live = () =>
      !signal.aborted && request.current === controller;

    setLoading(true);

    setSnapshot((previous) =>
      year != null &&
      previous &&
      (previous.year !== year || previous.term !== term)
        ? null
        : previous,
    );

    async function load() {
      try {
        // Сначала показываем сохранённые оценки.
        let data = await getJournalState(
          year,
          term,
          signal,
        );

        if (!live()) return;

        setSnapshot(data);
        setLoading(false);

        const key = `${data.year}:${data.term}`;

        if (lastAutoKey.current !== key) {
          lastAutoKey.current = key;
          setMessage("");

          if (data.is_current) {
            data = await autoSyncJournal(
              data.year,
              data.term,
              signal,
            );

            if (!live()) return;

            setSnapshot(data);
          }
        }

        // Пока задача работает, читаем только БД Altyn.
        const deadline = Date.now() + 5 * 60 * 1000;

        while (
          data.refresh_pending &&
          Date.now() < deadline
        ) {
          await pause(signal);

          if (!live()) return;

          data = await getJournalState(
            data.year,
            data.term,
            signal,
          );

          if (!live()) return;

          setSnapshot(data);
        }

        if (data.refresh_pending && live()) {
          setMessage(
            "Обновление занимает больше времени. " +
              "Нажмите «Проверить состояние» позже.",
          );
        }
      } catch (error) {
        if (!live() || error.name === "AbortError") {
          return;
        }

        if (error.status === 401) {
          expired.current();
        } else {
          setMessage(
            error.message || "Не удалось загрузить журнал.",
          );
        }
      } finally {
        if (live()) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      controller.abort();
      request.current?.abort();
    };
  }, [year, term, revision]);

  function recheck() {
    if (manual.current) return;

    setMessage("");
    setLoading(true);
    setRevision((value) => value + 1);
  }

  async function refresh() {
    if (!snapshot || loading || manual.current) {
      return;
    }

    manual.current = true;
    request.current?.abort();

    const controller = new AbortController();
    request.current = controller;

    setSyncing(true);
    setMessage("Получаем свежий журнал из Platonus…");

    try {
      const data = await syncJournal(
        snapshot.year,
        snapshot.term,
        controller.signal,
      );

      if (controller.signal.aborted) return;

      setSnapshot(data);
      setMessage(data.sync_message || "Журнал обновлён.");
    } catch (error) {
      if (
        controller.signal.aborted ||
        error.name === "AbortError"
      ) {
        return;
      }

      if (error.status === 401) {
        expired.current();
      } else {
        setMessage(
          error.message || "Обновление не выполнено.",
        );
      }
    } finally {
      manual.current = false;

      if (!controller.signal.aborted) {
        setSyncing(false);

        // Перечитываем результат из БД.
        // Повторный автоматический POST здесь не нужен.
        setRevision((value) => value + 1);
      }
    }
  }

  return {
    snapshot,
    loading,
    syncing,
    message,
    refresh,
    recheck,
  };
}