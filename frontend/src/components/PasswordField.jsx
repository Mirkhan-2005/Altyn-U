import { useState } from "react";

export default function PasswordField({
  id,
  label,
  ...inputProps
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>

      <div className="password-field">
        <input
          {...inputProps}
          id={id}
          name={id}
          type={visible ? "text" : "password"}
          required
        />

        <button
          type="button"
          className="password-toggle"
          disabled={inputProps.disabled}
          aria-controls={id}
          aria-pressed={visible}
          aria-label={
            visible ? "Скрыть пароль" : "Показать пароль"
          }
          onClick={() => setVisible((value) => !value)}
        >
          {visible ? "Скрыть" : "Показать"}
        </button>
      </div>
    </div>
  );
}