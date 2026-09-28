export default function SiteLayout({
  page,
  onNavigate,
  onLogout,
  children,
}) {
  return (
    <div className="portal">
      <header className="portal-header">
        <button
          type="button"
          className="portal-logo"
          onClick={() => onNavigate("home")}
        >
          altyn.
        </button>

        <nav aria-label="Главное меню">
          <button
            type="button"
            aria-current={page === "home" ? "page" : undefined}
            onClick={() => onNavigate("home")}
          >
            Главная
          </button>

          <button
            type="button"
            aria-current={page === "profile" ? "page" : undefined}
            onClick={() => onNavigate("profile")}
          >
            Профиль
          </button>
          
          <button
            type="button"
            aria-current={page === "journal" ? "page" : undefined}
            onClick={() => onNavigate("journal")}
          >
            Журнал
          </button>

          

          <button type="button" onClick={() => onLogout()}>
            Выйти
          </button>
        </nav>
      </header>



      <main className={
            page === "journal"
            ? "portal-main portal-main-journal"
            : "portal-main"
        }
        >
        {children}
</main>
    </div>
  );
}