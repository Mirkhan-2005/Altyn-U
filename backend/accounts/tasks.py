from celery import shared_task


@shared_task(
    name="accounts.check_queue",
    ignore_result=False,
)
def check_queue():
    return {
        "status": "ok",
        "message": "Фоновая задача Altyn выполнена.",
    }