from journal.models import JournalSnapshot

from .client import JournalSyncError, download_periods
from .sync import sync_journal


def discover_periods(user):
    first, warning = download_periods(user)

    warnings = [warning] if warning else []
    periods = []

    for year_option in first["years"]:
        year = year_option["value"]

        if year == first["selected_year"]:
            metadata = first
        else:
            metadata, warning = download_periods(
                user,
                year=year,
            )

            if warning:
                warnings.append(warning)

        # Для каждого года используем его собственный список периодов.
        # Наличие пункта в списке ещё не доказывает наличие оценок.
        for term_option in metadata["terms"]:
            periods.append({
                "year": year,
                "term": term_option["value"],
                "label": (
                    f"{year_option['label']}, "
                    f"период {term_option['label']}"
                ),
            })

    return periods, list(dict.fromkeys(warnings))


def import_history(
    user,
    *,
    refresh_existing=False,
    report=None,
):
    periods, warnings = discover_periods(user)

    result = {
        "total": len(periods),
        "saved": 0,
        "skipped": 0,
        "errors": [],
        "not_attempted": 0,
        "warnings": warnings,
    }

    for index, period in enumerate(periods, start=1):
        year = period["year"]
        term = period["term"]

        prefix = (
            f"[{index}/{len(periods)}] "
            f"{period['label']}"
        )

        # Повторный запуск продолжает импорт:
        # успешно сохранённые журналы пропускаются.
        cached = JournalSnapshot.objects.filter(
            user=user,
            year=year,
            term=term,
            last_synced_at__isnull=False,
        ).exists()

        if cached and not refresh_existing:
            result["skipped"] += 1

            if report:
                report(f"{prefix}: уже сохранён.")

            continue

        try:
            snapshot = sync_journal(
                user,
                year,
                term,
            )

        except JournalSyncError as exc:
            result["errors"].append({
                "year": year,
                "term": term,
                "message": str(exc),
            })

            if report:
                report(
                    f"{prefix}: не загружен. {exc}"
                )

            # Проблемы доступа, занятый журнал,
            # ограничения запросов или недоступность сервиса:
            # прекращаем новые попытки в этом запуске.
            if exc.status_code in {
                401, 403, 409, 429, 500, 503,
            }:
                result["not_attempted"] = (
                    len(periods) - index
                )
                break

        else:
            result["saved"] += 1

            if snapshot.sync_message:
                result["warnings"].append(
                    snapshot.sync_message
                )

            if report:
                report(f"{prefix}: сохранён.")

    result["warnings"] = list(
        dict.fromkeys(result["warnings"])
    )

    return result