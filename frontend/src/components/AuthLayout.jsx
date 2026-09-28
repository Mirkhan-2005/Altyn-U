export default function AuthLayout({ children }) {
  return (
    <main className="auth-layout">
      <aside className="brand-panel">
        <div className="brand">
          altyn<span>.</span>
        </div>

        <div className="brand-content">
          <span className="university-label">
            ДЛЯ СТУДЕНТОВ ЕНУ
          </span>

          <h2>
            Твой путь.
            <br />
            Твой <span>результат.</span>
          </h2>

          <p>Твоё студенческое пространство начинается здесь.</p>
        </div>

        <p className="brand-footer">
          Независимый студенческий проект
        </p>
      </aside>

      <div className="form-panel">
        {children}

        <footer className="page-footer">
          Altyn · ЕНУ
        </footer>
      </div>
    </main>
  );
}