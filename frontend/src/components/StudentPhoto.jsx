import { useEffect, useState } from "react";

import { getPhoto } from "../api/client";

export default function StudentPhoto({ onSessionExpired }) {
  const [src, setSrc] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    let active = true;
    let objectUrl;

    getPhoto(controller.signal)
      .then((blob) => {
        if (!active) return;

        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((error) => {
        if (!active || error.name === "AbortError") return;

        if (error.status === 401) {
          onSessionExpired();
        } else {
          setFailed(true);
        }
      });

    return () => {
      active = false;
      controller.abort();

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [onSessionExpired]);

  if (failed || !src) {
    return (
      <div className="student-photo photo-placeholder">
        {failed ? "Фото недоступно" : "Загружаем фото…"}
      </div>
    );
  }

  return (
    <img
      className="student-photo"
      src={src}
      alt="Фото студента"
      onError={() => setFailed(true)}
    />
  );
}