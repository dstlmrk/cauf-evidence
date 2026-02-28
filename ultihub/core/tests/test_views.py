import pytest
from django.test import Client


def test_homepage_head_request_returns_redirect(client: Client):
    response = client.head("/")
    assert response.status_code in (301, 302)


@pytest.mark.django_db
def test_tournaments_head_request_returns_ok(client: Client):
    response = client.head("/tournaments/")
    assert response.status_code == 200
