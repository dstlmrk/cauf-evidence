import io

from clubs.forms import ClubAdminForm, ClubLogoForm
from clubs.models import ClubLogo, ClubNotification
from clubs.services import (
    LOGO_LARGE_SIZE,
    LOGO_SMALL_SIZE,
    approve_club_logo,
    build_logo_variants,
    reject_club_logo,
    remove_club_logo,
    save_club_logo,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from guardian.shortcuts import assign_perm
from PIL import Image

from tests.conftest import with_app_settings
from tests.factories import (
    AgentAtClubFactory,
    AgentFactory,
    ClubFactory,
    UserFactory,
)
from tests.helpers import create_complete_competition


def uploaded_image(
    width: int = 400,
    height: int = 400,
    image_format: str = "PNG",
) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buffer, format=image_format)
    extension = image_format.lower()
    return SimpleUploadedFile(
        f"logo.{extension}",
        buffer.getvalue(),
        content_type=f"image/{extension}",
    )


def opened(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


class TestBuildLogoVariants:
    def test_renders_two_square_webp_variants(self):
        large, small = build_logo_variants(uploaded_image(400, 400))

        assert opened(large).format == "WEBP"
        assert opened(small).size == (LOGO_SMALL_SIZE, LOGO_SMALL_SIZE)

    def test_almost_square_input_is_padded_not_cropped(self):
        large, _ = build_logo_variants(uploaded_image(600, 560))
        image = opened(large).convert("RGBA")

        assert image.size == (LOGO_LARGE_SIZE, LOGO_LARGE_SIZE)
        # The thin padding sits above and below the source image, and must stay transparent
        assert image.getpixel((LOGO_LARGE_SIZE // 2, 2))[3] == 0
        assert image.getpixel((LOGO_LARGE_SIZE // 2, LOGO_LARGE_SIZE // 2))[3] == 255

    def test_small_input_is_not_upscaled(self):
        large, small = build_logo_variants(uploaded_image(300, 300))

        assert opened(large).size == (300, 300)
        assert opened(small).size == (LOGO_SMALL_SIZE, LOGO_SMALL_SIZE)


class TestClubLogoForm:
    def test_accepts_reasonable_image(self):
        form = ClubLogoForm({}, {"logo": uploaded_image(400, 400)})

        assert form.is_valid(), form.errors

    def test_rejects_too_small_image(self):
        form = ClubLogoForm({}, {"logo": uploaded_image(100, 100)})

        assert not form.is_valid()
        assert "shorter side" in str(form.errors["logo"])

    def test_rejects_non_square_image(self):
        form = ClubLogoForm({}, {"logo": uploaded_image(600, 400)})

        assert not form.is_valid()
        assert "Crop it to a square" in str(form.errors["logo"])

    def test_accepts_image_a_pixel_off_square(self):
        form = ClubLogoForm({}, {"logo": uploaded_image(400, 398)})

        assert form.is_valid(), form.errors

    def test_rejects_unsupported_format(self):
        form = ClubLogoForm({}, {"logo": uploaded_image(400, 400, image_format="GIF")})

        assert not form.is_valid()
        assert "Only PNG, JPEG and WebP" in str(form.errors["logo"])

    def test_rejects_non_image(self):
        form = ClubLogoForm({}, {"logo": SimpleUploadedFile("logo.png", b"not an image")})

        assert not form.is_valid()


class TestSaveAndApproveLogo:
    def test_save_stores_a_logo_waiting_for_approval(self):
        club = ClubFactory()

        logo = save_club_logo(club, uploaded_image())
        club.refresh_from_db()

        assert bytes(logo.large) and bytes(logo.small)
        assert not logo.is_approved
        assert club.logo_updated_at is None

    def test_save_replaces_only_the_logo_waiting_for_approval(self):
        club = ClubFactory()
        save_club_logo(club, uploaded_image(400, 400))
        save_club_logo(club, uploaded_image(300, 300))

        pending = ClubLogo.objects.get(club=club, is_approved=False)
        assert ClubLogo.objects.filter(club=club).count() == 1
        assert opened(bytes(pending.large)).size == (300, 300)

    def test_approve_puts_the_logo_in_use(self):
        club = ClubFactory()

        approve_club_logo(save_club_logo(club, uploaded_image()))
        club.refresh_from_db()

        logo = ClubLogo.objects.get(club=club)
        assert logo.is_approved
        assert logo.approved_at is not None
        assert club.logo_updated_at == logo.approved_at

    def test_approve_records_who_approved_it(self):
        club = ClubFactory()
        agent = AgentFactory()

        approve_club_logo(save_club_logo(club, uploaded_image()), approved_by=agent)

        assert ClubLogo.objects.get(club=club).approved_by == agent

    def test_previous_logo_stays_in_use_until_the_new_one_is_approved(self):
        club = ClubFactory()
        first = save_club_logo(club, uploaded_image(400, 400))
        approve_club_logo(first)

        save_club_logo(club, uploaded_image(300, 300))
        club.refresh_from_db()

        assert ClubLogo.objects.filter(club=club).count() == 2
        assert ClubLogo.objects.get(club=club, is_approved=True).pk == first.pk
        assert club.logo_updated_at == first.approved_at

    def test_approving_a_replacement_drops_the_previous_logo(self):
        club = ClubFactory()
        first = save_club_logo(club, uploaded_image(400, 400))
        approve_club_logo(first)
        second = save_club_logo(club, uploaded_image(300, 300))

        approve_club_logo(second)

        assert ClubLogo.objects.filter(club=club).count() == 1
        assert ClubLogo.objects.get(club=club).pk == second.pk

    def test_reject_removes_the_logo(self):
        club = ClubFactory()
        logo = save_club_logo(club, uploaded_image())

        reject_club_logo(logo)

        assert not ClubLogo.objects.filter(club=club).exists()

    def test_rejecting_a_logo_in_use_takes_it_out_of_use(self):
        club = ClubFactory()
        logo = save_club_logo(club, uploaded_image())
        approve_club_logo(logo)

        reject_club_logo(logo)
        club.refresh_from_db()

        assert club.logo_updated_at is None

    def test_remove_deletes_everything(self):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image(400, 400)))
        save_club_logo(club, uploaded_image(300, 300))

        remove_club_logo(club)
        club.refresh_from_db()

        assert not ClubLogo.objects.filter(club=club).exists()
        assert club.logo_updated_at is None

    def test_remove_pending_only_keeps_the_logo_in_use(self):
        club = ClubFactory()
        approved = save_club_logo(club, uploaded_image(400, 400))
        approve_club_logo(approved)
        save_club_logo(club, uploaded_image(300, 300))

        remove_club_logo(club, pending_only=True)
        club.refresh_from_db()

        assert list(ClubLogo.objects.filter(club=club).values_list("pk", flat=True)) == [
            approved.pk
        ]
        assert club.logo_updated_at == approved.approved_at


class TestLogoViews:
    @with_app_settings(club_logo_upload_enabled=True)
    def test_upload_queues_logo_for_approval(self, logged_in_client):
        club = ClubFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.post(reverse("clubs:upload_logo"), data={"logo": uploaded_image()})
        club.refresh_from_db()

        assert response.status_code == 302
        assert ClubLogo.objects.filter(club=club, is_approved=False).exists()
        assert club.logo_updated_at is None

    @with_app_settings(club_logo_upload_enabled=True)
    def test_upload_rejects_invalid_image(self, logged_in_client):
        club = ClubFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.post(
            reverse("clubs:upload_logo"),
            data={"logo": uploaded_image(100, 100)},
        )

        assert response.status_code == 302
        assert not ClubLogo.objects.filter(club=club).exists()

    @with_app_settings(club_logo_upload_enabled=True)
    def test_remove_deletes_logo(self, logged_in_client):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image()))
        client = logged_in_client(UserFactory(), club)

        response = client.post(reverse("clubs:remove_logo"))
        club.refresh_from_db()

        assert response.status_code == 204
        assert not ClubLogo.objects.filter(club=club).exists()
        assert club.logo_updated_at is None

    @with_app_settings(club_logo_upload_enabled=True)
    def test_cancel_pending_keeps_the_logo_in_use(self, logged_in_client):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image(400, 400)))
        save_club_logo(club, uploaded_image(300, 300))
        client = logged_in_client(UserFactory(), club)

        response = client.post(reverse("clubs:cancel_pending_logo"))
        club.refresh_from_db()

        assert response.status_code == 204
        assert ClubLogo.objects.filter(club=club, is_approved=True).count() == 1
        assert club.logo_updated_at is not None

    def test_serves_approved_logo_with_long_cache(self):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image()))

        response = Client().get(reverse("clubs:club_logo", args=[club.pk, "small"]))

        assert response.status_code == 200
        assert response["Content-Type"] == "image/webp"
        assert "immutable" in response["Cache-Control"]
        assert opened(response.content).size == (LOGO_SMALL_SIZE, LOGO_SMALL_SIZE)

    def test_does_not_serve_a_logo_waiting_for_approval(self):
        club = ClubFactory()
        save_club_logo(club, uploaded_image())

        response = Client().get(reverse("clubs:club_logo", args=[club.pk, "large"]))

        assert response.status_code == 404

    def test_returns_404_for_club_without_logo(self):
        club = ClubFactory()

        response = Client().get(reverse("clubs:club_logo", args=[club.pk, "large"]))

        assert response.status_code == 404

    @with_app_settings(club_logo_upload_enabled=True)
    def test_settings_page_previews_the_logo_waiting_for_approval(self, logged_in_client):
        club = ClubFactory()
        save_club_logo(club, uploaded_image())
        client = logged_in_client(UserFactory(), club)

        response = client.get(reverse("clubs:settings"))
        content = response.content.decode()

        assert response.status_code == 200
        assert reverse("clubs:upload_logo") in content
        assert "data:image/webp;base64," in content

    def test_upload_is_rejected_when_the_feature_is_off(self, logged_in_client):
        club = ClubFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.post(reverse("clubs:upload_logo"), data={"logo": uploaded_image()})

        assert response.status_code == 404
        assert not ClubLogo.objects.filter(club=club).exists()

    def test_settings_page_hides_the_form_when_the_feature_is_off(self, logged_in_client):
        club = ClubFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.get(reverse("clubs:settings"))

        assert response.status_code == 200
        assert reverse("clubs:upload_logo") not in response.content.decode()


class TestLogoInClubLists:
    def test_final_standings_modal_renders_the_logo(self):
        setup = create_complete_competition()
        club = setup["application"].team.club
        approve_club_logo(save_club_logo(club, uploaded_image()))

        response = Client().get(
            reverse(
                "competitions:competition_final_placements_dialog", args=[setup["competition"].id]
            )
        )

        assert response.status_code == 200
        assert reverse("clubs:club_logo", args=[club.pk, "small"]) in response.content.decode()

    def test_competition_application_list_renders_the_logo(self):
        setup = create_complete_competition()
        club = setup["application"].team.club
        approve_club_logo(save_club_logo(club, uploaded_image()))

        response = Client().get(
            reverse("competitions:application_list", args=[setup["competition"].id])
        )

        assert response.status_code == 200
        assert reverse("clubs:club_logo", args=[club.pk, "small"]) in response.content.decode()

    def test_tournament_teams_table_falls_back_to_the_short_name(self):
        setup = create_complete_competition()
        club = setup["application"].team.club
        club.short_name = "ABC"
        club.save()

        response = Client().get(reverse("tournaments:teams_table", args=[setup["tournament"].id]))

        assert response.status_code == 200
        assert "club-logo-empty" in response.content.decode()


class TestLogoAdmin:
    def admin_client(self, user_factory):
        client = Client()
        client.force_login(user_factory(is_staff=True, is_superuser=True))
        return client

    def test_approve_action_puts_the_logo_in_use(self, user_factory):
        club = ClubFactory()
        logo = save_club_logo(club, uploaded_image())

        response = self.admin_client(user_factory).post(
            reverse("admin:clubs_clublogo_changelist"),
            data={"action": "approve_logos", "_selected_action": [logo.pk]},
        )
        club.refresh_from_db()
        logo.refresh_from_db()

        assert response.status_code == 302
        assert logo.is_approved
        assert club.logo_updated_at is not None

    def test_reject_action_removes_the_logo(self, user_factory):
        club = ClubFactory()
        logo = save_club_logo(club, uploaded_image())

        self.admin_client(user_factory).post(
            reverse("admin:clubs_clublogo_changelist"),
            data={"action": "reject_logos", "_selected_action": [logo.pk]},
        )

        assert not ClubLogo.objects.filter(pk=logo.pk).exists()

    def test_changelist_previews_logos_inline(self, user_factory):
        club = ClubFactory()
        save_club_logo(club, uploaded_image())

        response = self.admin_client(user_factory).get(reverse("admin:clubs_clublogo_changelist"))

        assert response.status_code == 200
        assert "data:image/webp;base64," in response.content.decode()


class TestLogoInNavbarAndCards:
    def test_navbar_shows_the_logo_of_the_selected_club(self, logged_in_client):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image()))
        user = UserFactory()
        assign_perm("manage_club", user, club)
        client = logged_in_client(user, club)

        response = client.get(reverse("clubs:members"))

        assert response.status_code == 200
        assert reverse("clubs:club_logo", args=[club.pk, "small"]) in response.content.decode()

    def test_navbar_stays_clean_for_a_club_without_a_logo(self, logged_in_client):
        club = ClubFactory()
        user = UserFactory()
        assign_perm("manage_club", user, club)
        client = logged_in_client(user, club)

        response = client.get(reverse("clubs:members"))

        assert response.status_code == 200
        assert "club-logo-empty" not in response.content.decode()

    def test_tournament_card_shows_the_logos_of_the_winning_teams(self, logged_in_client):
        setup = create_complete_competition()
        club = setup["application"].team.club
        approve_club_logo(save_club_logo(club, uploaded_image()))
        tournament = setup["tournament"]
        tournament.winner_team = setup["team_at_tournament"]
        tournament.sotg_winner_team = setup["team_at_tournament"]
        tournament.save()
        client = logged_in_client(UserFactory(), ClubFactory())

        response = client.get(reverse("tournaments:tournaments"))
        content = response.content.decode()

        assert response.status_code == 200
        assert content.count(reverse("clubs:club_logo", args=[club.pk, "small"])) == 2


class TestLogoStampConsistency:
    def test_deleting_the_logo_directly_clears_the_stamp(self):
        club = ClubFactory()
        logo = save_club_logo(club, uploaded_image())
        approve_club_logo(logo)

        logo.delete()
        club.refresh_from_db()

        assert club.logo_updated_at is None

    def test_deleting_a_pending_logo_leaves_the_stamp_alone(self):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image(400, 400)))
        pending = save_club_logo(club, uploaded_image(300, 300))
        club.refresh_from_db()
        stamp = club.logo_updated_at

        pending.delete()
        club.refresh_from_db()

        assert club.logo_updated_at == stamp

    def test_admin_delete_action_clears_the_stamp(self, user_factory):
        club = ClubFactory()
        logo = save_club_logo(club, uploaded_image())
        approve_club_logo(logo)
        client = Client()
        client.force_login(user_factory(is_staff=True, is_superuser=True))

        client.post(
            reverse("admin:clubs_clublogo_changelist"),
            data={"action": "delete_selected", "_selected_action": [logo.pk], "post": "yes"},
        )
        club.refresh_from_db()

        assert not ClubLogo.objects.filter(pk=logo.pk).exists()
        assert club.logo_updated_at is None


class TestClubAdminLogoFields:
    def change_page(self, user_factory, club):
        client = Client()
        client.force_login(user_factory(is_staff=True, is_superuser=True))
        return client.get(reverse("admin:clubs_club_change", args=[club.pk]))

    def test_remove_checkbox_is_hidden_for_a_club_without_a_logo(self, user_factory):
        response = self.change_page(user_factory, ClubFactory())

        assert response.status_code == 200
        assert "Remove logo" not in response.content.decode()

    def test_remove_checkbox_is_offered_once_a_logo_exists(self, user_factory):
        club = ClubFactory()
        save_club_logo(club, uploaded_image())

        response = self.change_page(user_factory, club)

        assert response.status_code == 200
        assert "Remove logo" in response.content.decode()

    def test_admin_can_remove_the_logo_without_replacing_it(self, user_factory):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image()))
        client = Client()
        client.force_login(user_factory(is_staff=True, is_superuser=True))

        response = client.post(
            reverse("admin:clubs_club_change", args=[club.pk]),
            data={
                "name": club.name,
                "short_name": club.short_name,
                "email": club.email,
                "website": club.website,
                "city": club.city,
                "organization_name": club.organization_name,
                "identification_number": club.identification_number,
                "remove_logo": "on",
            },
        )
        club.refresh_from_db()

        assert response.status_code == 302
        assert not ClubLogo.objects.filter(club=club).exists()
        assert club.logo_updated_at is None

    def test_replacing_and_removing_at_once_is_refused(self):
        club = ClubFactory()
        save_club_logo(club, uploaded_image())

        form = ClubAdminForm(
            {"name": club.name, "remove_logo": True},
            {"logo": uploaded_image()},
            instance=club,
        )

        assert not form.is_valid()
        assert "not both at once" in str(form.errors["remove_logo"])


class TestLogoChangesAreSilent:
    def admin_client(self, user_factory):
        client = Client()
        client.force_login(user_factory(is_staff=True, is_superuser=True))
        return client

    def club_form_data(self, club, **extra):
        return {
            "name": club.name,
            "short_name": club.short_name,
            "email": club.email,
            "website": club.website,
            "city": club.city,
            "organization_name": club.organization_name,
            "identification_number": club.identification_number,
            **extra,
        }

    def test_admin_upload_notifies_nobody(self, user_factory):
        club = ClubFactory()
        AgentAtClubFactory(club=club)

        self.admin_client(user_factory).post(
            reverse("admin:clubs_club_change", args=[club.pk]),
            data=self.club_form_data(club, logo=uploaded_image()),
        )
        club.refresh_from_db()

        assert club.logo_updated_at is not None
        assert not ClubNotification.objects.exists()

    def test_admin_removal_notifies_nobody(self, user_factory):
        club = ClubFactory()
        approve_club_logo(save_club_logo(club, uploaded_image()))
        AgentAtClubFactory(club=club)

        self.admin_client(user_factory).post(
            reverse("admin:clubs_club_change", args=[club.pk]),
            data=self.club_form_data(club, remove_logo="on"),
        )

        assert not ClubLogo.objects.filter(club=club).exists()
        assert not ClubNotification.objects.exists()

    def test_approval_and_rejection_notify_nobody(self, user_factory):
        club = ClubFactory()
        AgentAtClubFactory(club=club)
        approve_club_logo(save_club_logo(club, uploaded_image()))
        reject_club_logo(ClubLogo.objects.get(club=club))

        assert not ClubNotification.objects.exists()
