"""Application tracking service."""

from agents.job.repositories.application_repo import ApplicationRepository


class TrackerService:
    def __init__(self, application_repo: ApplicationRepository):
        self._application_repo = application_repo

    def create(
        self,
        job_id: int,
        resume_id: int | None = None,
        cover_letter_id: int | None = None,
    ) -> dict:
        app_id = self._application_repo.create_application(
            job_id=job_id,
            resume_id=resume_id,
            cover_letter_id=cover_letter_id,
        )
        return self._application_repo.get_application(app_id)

    def update_status(self, app_id: int, status: str) -> dict:
        self._application_repo.update_status(app_id, status)
        return self._application_repo.get_application(app_id)

    def list_applications(self, status: str | None = None) -> list[dict]:
        return self._application_repo.list_applications(status=status)

    def get_application(self, app_id: int) -> dict | None:
        return self._application_repo.get_application(app_id)

    def get_status_history(self, app_id: int) -> list[dict]:
        return self._application_repo.get_status_history(app_id)
