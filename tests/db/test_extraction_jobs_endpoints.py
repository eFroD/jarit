"""HTTP contract of /api/v1/extraction-jobs (contracts/http-api.md)."""

import asyncio
import logging
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from jarit.integrations.credentials import set_secret
from jarit.db.models.api_keys import APIKey
from jarit.jobs import repository
from jarit.jobs.models import FailureReason, JobStatus
from jarit.jobs.runner import DbJobStore, ExtractionRunner
from tests.factories import make_response, recipe_dict

JOBS = "/api/v1/extraction-jobs"
NOT_FOUND = {"detail": "Extraction job not found"}
PUSH = "jarit.api.v1.endpoints.extraction_jobs.push_recipe_to_mealie"


def queued_job(db, user, url="https://example.com/v"):
    return repository.create_job(db, user.id, url, "english")


def completed_job(db, user, name="Soup"):
    job = queued_job(db, user)
    repository.start_job(db, job.id)
    repository.complete_job(db, job.id, make_response(name, suggested="Soup v2"))
    return job


def failed_job(db, user, reason=FailureReason.VIDEO_UNREACHABLE):
    job = queued_job(db, user)
    repository.fail_job(db, job.id, reason)
    return job


def running_job(db, user):
    job = queued_job(db, user)
    repository.start_job(db, job.id)
    return job


def store_mealie_credentials(db, user):
    entry = APIKey(user_id=user.id, service_name="mealie", base_url="https://m")
    set_secret(entry, "mealie-key")
    db.add(entry)
    db.commit()


# --- US1: submit, read, upload ----------------------------------------------


def test_submit_returns_queued_job_immediately(client, db, fake_runner):
    response = client.post(
        JOBS, json={"url": "https://example.com/reel/1", "target_language": "german"}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "QUEUED"
    assert body["video_url"] == "https://example.com/reel/1"
    assert body["target_language"] == "german"
    assert body["result"] is None
    assert fake_runner.submitted == [uuid.UUID(body["id"])]


def test_target_language_defaults_to_english(client):
    response = client.post(JOBS, json={"url": "https://example.com/reel/1"})
    assert response.json()["target_language"] == "english"


@pytest.mark.parametrize(
    "payload",
    [
        {"url": "not a url"},
        {"url": "https://example.com/v", "target_language": "   "},
        {"url": "https://example.com/v", "target_language": "x" * 65},
    ],
)
def test_invalid_input_creates_no_job(client, db, user, fake_runner, payload):
    assert client.post(JOBS, json=payload).status_code == 422
    assert repository.list_owned_jobs(db, user.id) == []
    assert fake_runner.submitted == []


def test_get_completed_job_contains_result(client, db, user):
    job = completed_job(db, user)

    body = client.get(f"{JOBS}/{job.id}").json()

    assert body["status"] == "COMPLETED"
    assert body["title"] == "Soup"
    assert body["result"]["recipe"]["name"] == "Soup"
    assert body["result"]["recipe"]["@type"] == "Recipe"
    assert body["result"]["suggested_version"]["name"] == "Soup v2"


@pytest.mark.parametrize("job_id", [str(uuid.uuid4()), "not-a-uuid"])
def test_unknown_job_is_404(client, job_id):
    response = client.get(f"{JOBS}/{job_id}")
    assert response.status_code == 404
    assert response.json() == NOT_FOUND


def test_upload_sets_flag_on_success(client, db, user):
    job = completed_job(db, user)
    store_mealie_credentials(db, user)

    with patch(PUSH, new_callable=AsyncMock, return_value="ok") as push:
        response = client.post(f"{JOBS}/{job.id}/upload-mealie")

    assert response.status_code == 200
    assert response.json()["uploaded_to_mealie_at"] is not None
    recipe, endpoint, key = push.await_args.args
    assert recipe["name"] == "Soup"
    assert (endpoint, key) == ("https://m", "mealie-key")
    assert client.get(f"{JOBS}/{job.id}").json()["uploaded_to_mealie_at"] is not None


def test_failed_upload_keeps_flag_unset(client, db, user):
    job = completed_job(db, user)
    store_mealie_credentials(db, user)
    error = httpx.HTTPStatusError(
        "bad",
        request=httpx.Request("POST", "https://m"),
        response=httpx.Response(502, text="mealie down"),
    )

    with patch(PUSH, new_callable=AsyncMock, side_effect=error):
        response = client.post(f"{JOBS}/{job.id}/upload-mealie")

    assert response.status_code == 502
    assert client.get(f"{JOBS}/{job.id}").json()["uploaded_to_mealie_at"] is None


def test_upload_requires_completed_job(client, db, user):
    job = running_job(db, user)
    store_mealie_credentials(db, user)
    response = client.post(f"{JOBS}/{job.id}/upload-mealie")
    assert response.status_code == 409


def test_old_endpoints_are_gone(client):
    assert client.post("/api/v1/recipes/extract-recipe", json={}).status_code == 404
    assert client.post("/api/v1/integrations/upload-mealie", json={}).status_code in (
        404,
        405,
    )


# --- US2: list for progress / dashboard -------------------------------------


def test_list_returns_own_jobs_newest_first_without_result(
    client, db, user, other_user
):
    first = completed_job(db, user, "First")
    second = queued_job(db, user, "https://example.com/second")
    queued_job(db, other_user)

    body = client.get(JOBS).json()

    assert [j["id"] for j in body] == [str(second.id), str(first.id)]
    assert body[1]["title"] == "First"
    assert body[0]["title"] is None
    assert all("result" not in j for j in body)


# --- US3: retry and no leaks -------------------------------------------------


def test_retry_failed_job(client, db, user, fake_runner):
    job = failed_job(db, user)

    response = client.post(f"{JOBS}/{job.id}/retry")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "QUEUED"
    assert body["failure_reason"] is None
    assert fake_runner.submitted == [job.id]


def test_retry_is_refused_unless_failed(client, db, user, fake_runner):
    for job in (queued_job(db, user), running_job(db, user), completed_job(db, user)):
        response = client.post(f"{JOBS}/{job.id}/retry")
        assert response.status_code == 409
        assert response.json() == {"detail": "Only failed extractions can be retried"}

    failed = failed_job(db, user)
    assert client.post(f"{JOBS}/{failed.id}/retry").status_code == 202
    assert client.post(f"{JOBS}/{failed.id}/retry").status_code == 409
    assert fake_runner.submitted == [failed.id]


def test_failure_details_stay_in_the_log(client, db, user, caplog):
    job = queued_job(db, user)

    async def extract(url, language, report):
        raise RuntimeError("SENTINEL-trace /srv/secret/path")

    async def run_once():
        runner = ExtractionRunner(limit=1, extract=extract, store=DbJobStore())
        runner.start()
        runner.submit(job.id)
        async with asyncio.timeout(5):
            while repository.get_owned_job(db, user.id, job.id).status != "FAILED":
                db.expire_all()
                await asyncio.sleep(0.02)
        await runner.stop()

    caplog.set_level(logging.ERROR)
    asyncio.run(run_once())

    response = client.get(f"{JOBS}/{job.id}")
    assert response.json()["failure_reason"] == FailureReason.UNKNOWN.value
    assert "SENTINEL" not in response.text
    assert "SENTINEL" in caplog.text
    assert any(getattr(r, "job_id", None) == str(job.id) for r in caplog.records)
    assert f"Extraction job {job.id} failed: UNKNOWN" in caplog.text


# --- US6: isolation ----------------------------------------------------------


@pytest.mark.parametrize("intruder", ["other_user", "admin_user"])
def test_foreign_jobs_look_missing(client, db, user, act_as, request, intruder):
    job = completed_job(db, user)
    failed = failed_job(db, user)
    act_as(request.getfixturevalue(intruder))

    calls = [
        client.get(f"{JOBS}/{job.id}"),
        client.put(f"{JOBS}/{job.id}/recipe", json=recipe_dict("Hijacked")),
        client.post(f"{JOBS}/{job.id}/upload-mealie"),
        client.post(f"{JOBS}/{failed.id}/retry"),
        client.delete(f"{JOBS}/{job.id}"),
    ]

    for response in calls:
        assert response.status_code == 404
        assert response.json() == NOT_FOUND
    assert client.get(JOBS).json() == []
    db.expire_all()
    assert repository.get_job(db, job.id).title == "Soup"


# --- US7: edit, upload edited version, delete -------------------------------


def test_edit_is_saved_and_uploaded(client, db, user):
    job = completed_job(db, user)
    store_mealie_credentials(db, user)

    response = client.put(f"{JOBS}/{job.id}/recipe", json=recipe_dict("Better soup"))

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Better soup"
    assert body["result"]["recipe"]["name"] == "Better soup"
    assert body["result"]["suggested_version"]["name"] == "Soup v2"

    with patch(PUSH, new_callable=AsyncMock, return_value="ok") as push:
        client.post(f"{JOBS}/{job.id}/upload-mealie")
    assert push.await_args.args[0]["name"] == "Better soup"


def test_invalid_edit_is_rejected_and_keeps_recipe(client, db, user):
    job = completed_job(db, user)
    broken = recipe_dict()
    del broken["recipeIngredient"]

    assert client.put(f"{JOBS}/{job.id}/recipe", json=broken).status_code == 422
    assert client.get(f"{JOBS}/{job.id}").json()["result"]["recipe"]["name"] == "Soup"


def test_edit_requires_completed_job(client, db, user):
    job = running_job(db, user)
    response = client.put(f"{JOBS}/{job.id}/recipe", json=recipe_dict())
    assert response.status_code == 409


def test_delete_finished_jobs(client, db, user):
    for job_id in (completed_job(db, user).id, failed_job(db, user).id):
        assert client.delete(f"{JOBS}/{job_id}").status_code == 204
        assert client.get(f"{JOBS}/{job_id}").status_code == 404


def test_delete_refused_while_waiting_or_running(client, db, user):
    for job in (queued_job(db, user), running_job(db, user)):
        response = client.delete(f"{JOBS}/{job.id}")
        assert response.status_code == 409
        assert "Wait until the extraction has finished" in response.json()["detail"]


def test_status_values_match_contract():
    assert {s.value for s in JobStatus} == {
        "QUEUED",
        "FETCHING_DESCRIPTION",
        "TRANSCRIBING",
        "EXTRACTING",
        "COMPLETED",
        "FAILED",
    }
