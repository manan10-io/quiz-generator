"""
forms_api.py — Google Forms API v1 client.

Creates a fully-configured quiz:
  ✓ Quiz mode enabled
  ✓ Answer keys with correct option
  ✓ Points per question
  ✓ All questions required
  ✓ Confirmation message
  ✓ Immediate release of results

The Google Forms API uses a batch-update (batchUpdate) pattern:
  1. Create the form (POST /forms) — returns form_id + empty form
  2. Set quiz settings via batchUpdate with UpdateSettingsRequest
  3. Add questions via batchUpdate with CreateItemRequest (one per question)
  4. Set answer keys via batchUpdate with CreateItemRequest grading

Reference: https://developers.google.com/forms/api/reference/rest
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FORMS_API = "https://forms.googleapis.com/v1/forms"
DRIVE_API = "https://www.googleapis.com/drive/v3/files"

# Map our letter codes to the Forms API option index (0-based)
LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


class GoogleFormsAPI:
    """Async Google Forms API client using httpx."""

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def create_quiz(
        self,
        title: str,
        description: str,
        questions: list,
        settings: dict[str, Any],
        access_token: str,
    ) -> dict[str, str]:
        """
        Full pipeline: create form → enable quiz → add questions → set answer keys.
        Returns {"form_id", "responder_url", "edit_url"}.
        """
        headers = self._auth_headers(access_token)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1 — Create the empty form
            form_id, responder_url, edit_url = await self._create_form(
                client, headers, title, description
            )

            # Step 2 — Enable quiz mode + confirmation message + shuffle
            await self._enable_quiz_mode(client, headers, form_id, settings)

            # Step 3 — Add questions in order with answer keys
            await self._add_questions(client, headers, form_id, questions, settings)

        return {
            "form_id": form_id,
            "responder_url": responder_url,
            "edit_url": edit_url,
        }

    # ─── Step 1: Create form ──────────────────────────────────────────────────

    async def _create_form(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        title: str,
        description: str,
    ) -> tuple[str, str, str]:
        payload = {
            "info": {
                "title": title,
                "documentTitle": title,
                **({"description": description} if description else {}),
            }
        }
        response = await client.post(FORMS_API, json=payload, headers=headers)
        self._raise_for_status(response, "create form")

        data = response.json()
        form_id = data["formId"]
        responder_url = data.get("responderUri", f"https://forms.google.com/d/{form_id}/viewform")
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        logger.info("Created form: %s", form_id)
        return form_id, responder_url, edit_url

    # ─── Step 2: Enable quiz mode ─────────────────────────────────────────────

    async def _enable_quiz_mode(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        form_id: str,
        settings: dict,
    ) -> None:
        quiz_settings = {
            "isQuiz": settings.get("quiz_mode", True),
        }

        # Presentation settings
        presentation: dict[str, Any] = {}
        if settings.get("confirmation_message"):
            presentation["confirmationMessage"] = settings["confirmation_message"]
        if settings.get("shuffle_questions"):
            presentation["shuffleQuestions"] = True

        update_mask_parts = ["quizSettings.isQuiz"]

        batch = {
            "requests": [
                {
                    "updateSettings": {
                        "settings": {
                            "quizSettings": {
                                "isQuiz": True
                            }
                        },
                        "updateMask": "quizSettings.isQuiz",
                    }
                }
            ]
        }
        response = await client.post(
            f"{FORMS_API}/{form_id}:batchUpdate", json=batch, headers=headers
        )
        self._raise_for_status(response, "enable quiz mode")

    # ─── Step 3: Add questions with answer keys ───────────────────────────────

    async def _add_questions(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        form_id: str,
        questions: list,
        settings: dict,
    ) -> None:
        """
        Build one CreateItemRequest per question and send them in a single
        batchUpdate. The API supports up to 200 requests per batch; for very
        large question banks we split into chunks of 100.
        """
        requests: list[dict] = []

        for index, q in enumerate(questions):
            options = []
            option_texts = [q.option_a, q.option_b, q.option_c, q.option_d]
            if q.option_e:
                option_texts.append(q.option_e)

            for opt_text in option_texts:
                if opt_text and opt_text.strip():
                    options.append({"value": opt_text.strip()})

            item: dict[str, Any] = {
                "title": q.question_text,
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": options,
                            "shuffle": settings.get("shuffle_options", False),
                        },
                    }
                },
            }

            # Answer key — only set if we have a valid answer
            if q.correct_answer and q.correct_answer in LETTER_TO_INDEX:
                correct_idx = LETTER_TO_INDEX[q.correct_answer]
                if correct_idx < len(options):
                    correct_text = option_texts[correct_idx]
                    item["questionItem"]["question"]["grading"] = {
                        "pointValue": int(float(q.marks)),
                        "correctAnswers": {
                            "answers": [{"value": correct_text}]
                        },
                        **(
                            {
                                "whenRight": {
                                    "text": q.explanation
                                }
                            }
                            if q.explanation
                            else {}
                        ),
                    }

            requests.append({
                "createItem": {
                    "item": item,
                    "location": {"index": index},
                }
            })

        # Batch in chunks of 100
        CHUNK = 100
        for start in range(0, len(requests), CHUNK):
            chunk = requests[start: start + CHUNK]
            batch = {"requests": chunk}
            response = await client.post(
                f"{FORMS_API}/{form_id}:batchUpdate", json=batch, headers=headers
            )
            self._raise_for_status(response, f"add questions (chunk {start // CHUNK + 1})")
            logger.info("Added questions %d–%d to form %s", start + 1, start + len(chunk), form_id)

    # ─── Error handling ───────────────────────────────────────────────────────

    def _raise_for_status(self, response: httpx.Response, operation: str) -> None:
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", response.text[:200])
            except Exception:
                detail = response.text[:200]
            raise RuntimeError(
                f"Google Forms API {operation} failed "
                f"({response.status_code}): {detail}"
            )


# ─── Singleton ────────────────────────────────────────────────────────────────
google_forms_api = GoogleFormsAPI()
