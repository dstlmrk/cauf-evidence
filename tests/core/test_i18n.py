from django.test import Client
from django.urls import reverse


class TestLanguageSwitching:
    def test_default_language_is_english(self, client: Client):
        response = client.get("/")
        content = response.content.decode()
        assert 'lang="en"' in content

    def test_switch_to_czech(self, client: Client):
        response = client.post(
            reverse("set_language"),
            {"language": "cs", "next": "/"},
            follow=True,
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert 'lang="cs"' in content

    def test_switch_to_english_from_czech(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "cs", "next": "/"},
        )
        response = client.post(
            reverse("set_language"),
            {"language": "en", "next": "/"},
            follow=True,
        )
        content = response.content.decode()
        assert 'lang="en"' in content

    def test_language_persists_across_requests(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "cs", "next": "/"},
        )
        response = client.get("/")
        content = response.content.decode()
        assert 'lang="cs"' in content

    def test_set_language_requires_post(self, client: Client):
        response = client.get(reverse("set_language"))
        assert response.status_code == 405

    def test_invalid_language_falls_back_to_default(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "xx", "next": "/"},
        )
        response = client.get("/")
        content = response.content.decode()
        assert 'lang="en"' in content

    def test_browser_accept_language_czech(self, client: Client):
        response = client.get("/", headers={"Accept-Language": "cs"})
        content = response.content.decode()
        assert 'lang="cs"' in content

    def test_session_overrides_browser_language(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "en", "next": "/"},
        )
        response = client.get("/", headers={"Accept-Language": "cs"})
        content = response.content.decode()
        assert 'lang="en"' in content

    def test_language_switcher_visible_in_footer(self, client: Client):
        response = client.get("/")
        content = response.content.decode()
        assert 'name="language"' in content
        assert 'value="cs"' in content

    def test_language_switcher_shows_other_option_when_czech(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "cs", "next": "/"},
        )
        response = client.get("/")
        content = response.content.decode()
        assert 'value="en"' in content


class TestTranslatedContent:
    def test_navigation_in_english(self, client: Client):
        response = client.get("/")
        content = response.content.decode()
        assert "Competitions" in content
        assert "Tournaments" in content

    def test_navigation_in_czech(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "cs", "next": "/"},
        )
        response = client.get("/")
        content = response.content.decode()
        assert "Soutěže" in content
        assert "Turnaje" in content

    def test_privacy_policy_translated(self, client: Client):
        client.post(
            reverse("set_language"),
            {"language": "cs", "next": "/"},
        )
        response = client.get("/")
        content = response.content.decode()
        assert "Ochrana osobních údajů" in content

    def test_nsa_footer_always_czech(self, client: Client):
        response = client.get("/")
        content = response.content.decode()
        assert "Národní sportovní agentury" in content

        client.post(reverse("set_language"), {"language": "cs", "next": "/"})
        response = client.get("/")
        content = response.content.decode()
        assert "Národní sportovní agentury" in content
