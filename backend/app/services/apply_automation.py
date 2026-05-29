"""Apply automation — submits job applications on behalf of the user.

Supports Greenhouse boards via their public application API.
Additional ATS providers can be added by implementing new *Applicator classes.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import get_settings
from app.models.job import Job
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)
settings = get_settings()


GREENHOUSE_URL_PATTERN = re.compile(
    r"boards\.greenhouse\.io/([^/]+)/jobs/(\d+)"
)


@dataclass
class ApplicationResult:
    success: bool = False
    message: str = ""
    ats_type: str = ""


class GreenhouseApplicator:
    """Submit applications via Greenhouse public boards API.

    Docs: https://developers.greenhouse.io/job-board.html#submit-application
    """

    def submit(
        self,
        job: Job,
        profile: UserProfile,
        user_email: str = "",
        user_name: str = "",
    ) -> ApplicationResult:
        match = GREENHOUSE_URL_PATTERN.search(job.url or "")
        if not match:
            board_token = self._extract_board_from_source(job.source)
            job_id = None
        else:
            board_token = match.group(1)
            job_id = match.group(2)

        if not board_token:
            return ApplicationResult(
                success=False,
                message="Could not determine Greenhouse board token from job URL or source",
                ats_type="greenhouse",
            )

        if not job_id:
            job_id = self._extract_job_id_from_source(job.source)

        if not job_id:
            return ApplicationResult(
                success=False,
                message="Could not determine Greenhouse job ID",
                ats_type="greenhouse",
            )

        payload = self._build_application_payload(profile, user_email, user_name)

        url = (
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}"
            f"/jobs/{job_id}/application"
        )

        try:
            resp = httpx.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return ApplicationResult(
                success=True,
                message=f"Application submitted successfully to {board_token} (job {job_id})",
                ats_type="greenhouse",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Greenhouse apply failed [%d]: %s",
                e.response.status_code,
                e.response.text[:500],
            )
            return ApplicationResult(
                success=False,
                message=f"Greenhouse API error: {e.response.status_code} — {e.response.text[:200]}",
                ats_type="greenhouse",
            )
        except httpx.RequestError as e:
            logger.error("Greenhouse apply request error: %s", e)
            return ApplicationResult(
                success=False,
                message=f"Network error: {e}",
                ats_type="greenhouse",
            )

    def _extract_board_from_source(self, source: str) -> Optional[str]:
        if not source or not source.startswith("greenhouse"):
            return None
        parts = source.split(":", 1)
        return parts[1].strip() if len(parts) > 1 else None

    def _extract_job_id_from_source(self, source: str) -> Optional[str]:
        return None

    def _build_application_payload(
        self,
        profile: UserProfile,
        user_email: str,
        user_name: str,
    ) -> dict:
        first_name = "User"
        last_name = ""
        if user_name:
            parts = user_name.strip().split(None, 1)
            first_name = parts[0] if parts else "User"
            last_name = parts[1] if len(parts) > 1 else ""

        payload: dict = {
            "first_name": first_name,
            "last_name": last_name,
        }

        if user_email:
            payload["email"] = user_email
        if profile.phone:
            payload["phone"] = profile.phone
        if profile.linkedin_url:
            payload["linkedin_url"] = profile.linkedin_url
        if profile.github_url:
            payload["github_url"] = profile.github_url
        if profile.portfolio_url:
            payload["portfolio_url"] = profile.portfolio_url
        if profile.cover_letter_intro:
            payload["cover_letter"] = profile.cover_letter_intro
        if profile.how_did_you_hear:
            payload["how_did_you_hear"] = [{"value": profile.how_did_you_hear}]

        return payload


class ExternalUrlApplicator:
    """Fallback applicator for jobs that link to external sites (non-ATS)."""

    def submit(
        self,
        job: Job,
        profile: UserProfile,
        user_email: str = "",
        user_name: str = "",
    ) -> ApplicationResult:
        logger.info(
            "External URL job (no ATS detected) — marked applied: %s",
            job.url,
        )
        return ApplicationResult(
            success=True,
            message="Job links to an external site. Marked as applied — please submit manually.",
            ats_type="external",
        )


def get_applicator(job: Job):
    if job.source and job.source.startswith("greenhouse"):
        return GreenhouseApplicator()
    if job.url and "greenhouse.io" in job.url:
        return GreenhouseApplicator()
    return ExternalUrlApplicator()


def apply_to_job(
    job: Job,
    profile: UserProfile,
    user_email: str = "",
    user_name: str = "",
) -> ApplicationResult:
    applicator = get_applicator(job)
    logger.info(
        "Applying to job %d (%s) using %s",
        job.id,
        job.title,
        type(applicator).__name__,
    )
    return applicator.submit(job, profile, user_email, user_name)
