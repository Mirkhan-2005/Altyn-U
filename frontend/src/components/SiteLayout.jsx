export default function SiteLayout({
  page,
  onNavigate,
  onLogout,
  children,
  mainClassName = "",
}) {
  const navigation = [
    { page: "home", label: "Главная" },
    { page: "profile", label: "Профиль" },
    { page: "ranking", label: "Рейтинг" },
    { page: "journal", label: "Журнал" },
    { page: "teachers", label: "Преподаватели" },
    { page: "calculator", label: "Журнал-калькулятор" },
  ];

  
  const mainClasses = [
    "portal-main",
    page === "journal" || page === "calculator"
      ? "portal-main-journal"
      : "",
    mainClassName,
  ]
    .filter(Boolean)
    .join(" ");

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
          {navigation.map((item) => (
            <button
              key={item.page}
              type="button"
              aria-current={
                page === item.page ? "page" : undefined
              }
              onClick={() => onNavigate(item.page)}
            >
              {item.label}
            </button>
          ))}

          <button
            type="button"
            onClick={() => onLogout()}
          >
            Выйти
          </button>
        </nav>
      </header>

      <main className={mainClasses}>
        {children}
      </main>
    </div>
  );
}