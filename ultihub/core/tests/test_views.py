from django.test import Client


def test_homepage_head_request_returns_redirect(client: Client):
    response = client.head("/")
    assert response.status_code in (301, 302)
