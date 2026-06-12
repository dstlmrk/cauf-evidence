import logging
from datetime import date
from decimal import Decimal
from typing import Any, Literal, TypedDict

import requests
from requests.auth import HTTPBasicAuth
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt

from ultihub.settings import (
    ENVIRONMENT,
    FAKTUROID_BASE_URL,
    FAKTUROID_CLIENT_ID,
    FAKTUROID_CLIENT_SECRET,
    FAKTUROID_SLUG,
    FAKTUROID_USER_AGENT,
)

type InvoiceStatus = Literal["open", "sent", "overdue", "paid", "cancelled", "uncollectible"]


class InvoiceDetails(TypedDict):
    status: InvoiceStatus
    total: Decimal
    due_on: date | None


logger = logging.getLogger(__name__)

# (connect, read) timeout in seconds. A bounded timeout prevents a request from hanging
# indefinitely, which is critical for invoice creation where a stuck request would otherwise
# hold DB locks and leave the invoice in DRAFT, triggering a duplicate on the next resend.
HTTP_TIMEOUT = (5, 30)


class AuthorizationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class UnexpectedResponse(Exception):
    pass


class FakturoidClient:
    def __init__(self, client_id: str, client_secret: str, slug: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.slug = slug
        self.headers = {
            "Authorization": None,
            "User-Agent": FAKTUROID_USER_AGENT,
        }

    def _authorize(self, retry_state: RetryCallState) -> None:
        """
        https://www.fakturoid.cz/api/v3/authorization
        """
        response = requests.post(
            FAKTUROID_BASE_URL + "/oauth/token",
            json={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            headers={"Accept": "application/json", "User-Agent": FAKTUROID_USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )

        if response.status_code == 200:
            self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        else:
            logger.error("Error while authorizing to Fakturoid API: %s", response.status_code)
            raise AuthorizationError

    def _retry_request(self, method: str, url: str, json: dict) -> requests.Response:
        return retry(
            retry=retry_if_exception_type(AuthorizationError),
            stop=stop_after_attempt(2),
            reraise=True,
            before_sleep=self._authorize,
        )(self._request)(method, url, json)

    def _request(self, method: str, url: str, json: dict) -> requests.Response:
        response = getattr(requests, method)(
            url, headers=self.headers, json=json, timeout=HTTP_TIMEOUT
        )
        if response.status_code == 401:
            raise AuthorizationError
        if response.status_code == 404:
            raise NotFoundError
        return response

    def get(self, url: str) -> requests.Response:
        return self._retry_request("get", url, {})

    def post(self, url: str, json: dict) -> requests.Response:
        return self._retry_request("post", url, json)

    def create_invoice(
        self, subject_id: int, lines: list[dict[str, Any]], custom_id: str | None = None
    ) -> dict:
        """
        Create an invoice for the given subject with the given text and price.

        custom_id is our own stable identifier (the local Invoice id). It lets us deduplicate:
        if a previous create call timed out after Fakturoid had already stored the invoice, the
        retry can look the invoice up by custom_id instead of creating a duplicate.

        https://www.fakturoid.cz/api/v3/invoices#create-invoice
        """
        payload: dict[str, Any] = {
            "subject_id": subject_id,
            "lines": lines,
            "tags": ["created-by-evidence"],
        }
        if custom_id is not None:
            payload["custom_id"] = custom_id

        response = self.post(
            FAKTUROID_BASE_URL + f"/accounts/{self.slug}/invoices.json",
            payload,
        )

        if response.status_code == 201:
            return self._unpack_invoice(response.json())
        else:
            raise UnexpectedResponse(
                f"Error while creating invoice: {response.status_code}, {response.json()}"
            )

    def find_invoice_by_custom_id(self, custom_id: str) -> dict | None:
        """
        Return the invoice previously created with the given custom_id, or None if none exists.

        Used for idempotent retries: before creating an invoice again we check whether Fakturoid
        already has it (e.g. the original create succeeded but its response was lost to a timeout).

        https://www.fakturoid.cz/api/v3/invoices#invoices-index
        """
        response = self.get(
            FAKTUROID_BASE_URL + f"/accounts/{self.slug}/invoices.json?custom_id={custom_id}"
        )

        if response.status_code == 200:
            invoices = response.json()
            if invoices:
                return self._unpack_invoice(invoices[0])
            return None
        else:
            raise UnexpectedResponse(
                f"Error while searching invoice by custom_id: {response.status_code},"
                f" {response.json()}"
            )

    @staticmethod
    def _unpack_invoice(data: dict) -> dict:
        invoice_id = data["id"]
        logger.info("Fakturoid invoice %s", invoice_id)
        return {
            "invoice_id": invoice_id,
            "status": data["status"],
            "total": data["total"],
            "public_html_url": data["public_html_url"],
        }

    def get_invoice_details(self, invoice_id: int) -> InvoiceDetails:
        """
        Return details of the invoice with the given ID.

        https://www.fakturoid.cz/api/v3/invoices
        """
        response = self.get(
            FAKTUROID_BASE_URL + f"/accounts/{self.slug}/invoices/{invoice_id}.json"
        )

        if response.status_code == 200:
            data = response.json()
            due_on = date.fromisoformat(data["due_on"]) if data.get("due_on") else None
            return InvoiceDetails(
                status=data["status"],
                total=Decimal(data["total"]),
                due_on=due_on,
            )
        else:
            raise UnexpectedResponse(
                f"Error while getting invoice details: {response.status_code}, {response.json()}"
            )

    def get_subject_detail(self, subject_id: int) -> dict:
        """
        Return the details of the subject with the given ID.

        https://www.fakturoid.cz/api/v3/subjects#subject-detail
        """
        response = self.get(
            FAKTUROID_BASE_URL + f"/accounts/{self.slug}/subjects/{subject_id}.json"
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise UnexpectedResponse(
                f"Error while getting subject detail: {response.status_code}, {response.json()}"
            )


class FakturoidFakeClient:
    def create_invoice(
        self, subject_id: int, lines: list[dict[str, Any]], custom_id: str | None = None
    ) -> dict:
        return {"invoice_id": 1, "status": "open", "total": 100, "public_html_url": ""}

    def find_invoice_by_custom_id(self, custom_id: str) -> dict | None:
        return None

    def get_invoice_details(self, invoice_id: int) -> InvoiceDetails:
        return InvoiceDetails(status="open", total=Decimal(100), due_on=None)

    def get_subject_detail(self, subject_id: int) -> dict:
        return {}


if ENVIRONMENT == "prod" or (FAKTUROID_CLIENT_ID and FAKTUROID_CLIENT_SECRET and FAKTUROID_SLUG):
    fakturoid_client = FakturoidClient(
        FAKTUROID_CLIENT_ID,
        FAKTUROID_CLIENT_SECRET,
        FAKTUROID_SLUG,
    )
else:
    fakturoid_client = FakturoidFakeClient()  # type: ignore
