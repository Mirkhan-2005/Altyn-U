import { useEffect, useRef, useState } from "react";

import { resetAltynPassword } from "../api/client";
import PasswordField from "../components/PasswordField";


export default function PasswordResetForm({
  initialIin = "",
  onBack,
  onSuccess,
}) {
  const [iin, setIin] = useState(initialIin);
  const [platonusPassword, setPlatonusPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const pending = useRef(null);

  useEffect(() => {
    return () => pending.current?.abort();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();

    if (pending.current) return;

    if (!/^[0-9]{12}$/.test(iin) || !platonusPassword) {
      setMessage("Введите ИИН из 12 цифр и пароль Platonus.");
      return;
    }

    if (newPassword.length < 8) {
      setMessage("Новый пароль должен содержать минимум 8 символов.");
      return;
    }

    if (newPassword !== confirm) {
      setMessage("Новые пароли не совпадают.");
      return;
    }

    const controller = new AbortController();
    pending.current = controller;

    setBusy(true);
    setMessage("Проверяем Platonus и меняем пароль…");

    try {
      const result = await resetAltynPassword(
        iin,
        platonusPassword,
        newPassword,
        confirm,
        controller.signal,
      );

      if (!controller.signal.aborted) {
        onSuccess(iin, result.message);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setMessage(error.message || "Не удалось изменить пароль.");
      }
    } finally {
      if (!controller.signal.aborted) {
        setPlatonusPassword("");
        setNewPassword("");
        setConfirm("");
        setBusy(false);
      }

      pending.current = null;
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-heading">
        <span className="auth-label">
          ВОССТАНОВЛЕНИЕ ДОСТУПА
        </span>

        <h1>Забыли пароль?</h1>

        <p>
          Подтверди вход в Platonus и задай новый пароль Altyn.
          Пароль в самом Platonus не изменится.
        </p>
      </div>

      <form onSubmit={handleSubmit} aria-busy={busy}>
        <div className="form-field">
          <label htmlFor="reset-iin">ИИН</label>

          <input
            id="reset-iin"
            name="username"
            type="text"
            inputMode="numeric"
            autoComplete="username"
            placeholder="Введите 12 цифр"
            pattern="[0-9]{12}"
            maxLength={12}
            required
            autoFocus
            disabled={busy}
            value={iin}
            onChange={(event) =>
              setIin(
                event.target.value.replace(/\D/g, "").slice(0, 12),
              )
            }
          />
        </div>

        <PasswordField
          id="reset-platonus"
          label="Текущий пароль Platonus"
          autoComplete="off"
          placeholder="Пароль от Platonus"
          maxLength={256}
          value={platonusPassword}
          disabled={busy}
          onChange={(event) =>
            setPlatonusPassword(event.target.value)
          }
        />

        <PasswordField
          id="reset-new-password"
          label="Новый пароль Altyn"
          autoComplete="new-password"
          placeholder="Минимум 8 символов"
          minLength={8}
          maxLength={128}
          value={newPassword}
          disabled={busy}
          onChange={(event) =>
            setNewPassword(event.target.value)
          }
        />

        <PasswordField
          id="reset-password-confirm"
          label="Повтори новый пароль Altyn"
          autoComplete="new-password"
          placeholder="Введите новый пароль ещё раз"
          minLength={8}
          maxLength={128}
          value={confirm}
          disabled={busy}
          onChange={(event) => setConfirm(event.target.value)}
        />

        <div role="status" aria-live="polite">
          {message && (
            <p className="form-message">{message}</p>
          )}
        </div>

        <button
          type="submit"
          className="button button-primary"
          disabled={busy}
        >
          {busy ? "Проверяем…" : "Изменить пароль Altyn"}
        </button>
      </form>

      <button
        type="button"
        className="button button-secondary"
        style={{ marginTop: 12 }}
        disabled={busy}
        onClick={onBack}
      >
        Вернуться ко входу
      </button>
    </section>
  );
}