import { useEffect, useState } from "react";

import { getTeacherPhoto } from "../api/teachers";

export default function TeacherPhoto({
  teacher,
  onSessionExpired,
}) {
  const [src, setSrc] = useState("");
  const [failed, setFailed] = useState(false);

  const name = teacher.full_name || teacher.display_name;
  const available = Boolean(teacher.photo_url);

  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => Array.from(part)[0] || "")
    .join("")
    .toLocaleUpperCase("ru-RU");

  useEffect(() => {
    if (!available) return;

    const controller = new AbortController();
    let objectUrl = "";

    getTeacherPhoto(teacher.id, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;

        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((error) => {
        if (
          controller.signal.aborted ||
          error.name === "AbortError"
        ) {
          return;
        }

        if (error.status === 401) {
          onSessionExpired();
        } else {
          setFailed(true);
        }
      });

    return () => {
      controller.abort();

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [teacher.id, available, onSessionExpired]);

  if (src && !failed) {
    return (
      <img
        className="teacher-photo"
        src={src}
        alt={`Фото: ${name}`}
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <div
      className="teacher-photo teacher-photo-placeholder"
      aria-label={`Фотография недоступна: ${name}`}
    >
      {initials || "?"}
    </div>
  );
}