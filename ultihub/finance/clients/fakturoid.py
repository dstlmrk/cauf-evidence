import logging
from typing import Any, Literal

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

logger = logging.getLogger(__name__)


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
        response = getattr(requests, method)(url, headers=self.headers, json=json)
        if response.status_code == 401:
            raise AuthorizationError
        if response.status_code == 404:
            raise NotFoundError
        return response

    def get(self, url: str) -> requests.Response:
        return self._retry_request("get", url, {})

    def post(self, url: str, json: dict) -> requests.Response:
        return self._retry_request("post", url, json)

    def create_invoice(self, subject_id: int, lines: list[dict[str, Any]]) -> dict:
        """
        Create an invoice for the given subject with the given text and price.

        https://www.fakturoid.cz/api/v3/invoices#create-invoice
        """
        response = self.post(
            FAKTUROID_BASE_URL + f"/accounts/{self.slug}/invoices.json",
            {
                "subject_id": subject_id,
                "lines": lines,
                "tags": ["created-by-evidence"],
            },
        )

        if response.status_code == 201:
            unpacked_response = response.json()
            invoice_id = unpacked_response["id"]
            logger.info("Successfully created invoice %s", invoice_id)
            return {
                "invoice_id": invoice_id,
                "status": unpacked_response["status"],
                "total": unpacked_response["total"],
                "public_html_url": unpacked_response["public_html_url"],
            }
        else:
            raise UnexpectedResponse(
                f"Error while creating invoice: {response.status_code}, {response.json()}"
            )

    def get_invoice_status(self, invoice_id: int) -> InvoiceStatus:
        """
        Return the status of the invoice with the given ID.
        Possible values are: open, sent, overdue, paid, cancelled, uncollectible.

        https://www.fakturoid.cz/api/v3/invoices#invoice-status-table
        """
        response = self.get(
            FAKTUROID_BASE_URL + f"/accounts/{self.slug}/invoices/{invoice_id}.json"
        )

        if response.status_code == 200:
            return response.json()["status"]
        else:
            raise UnexpectedResponse(
                f"Error while getting invoice status: {response.status_code}, {response.json()}"
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
    def create_invoice(self, subject_id: int, lines: list[dict[str, Any]]) -> dict:
        return {"invoice_id": 1, "status": "open", "total": 100, "public_html_url": ""}

    def get_invoice_status(self, invoice_id: int) -> InvoiceStatus:
        return "open"

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
