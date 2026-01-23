from unittest.mock import MagicMock, patch

from core.tasks import send_email


class TestSendEmail:
    @patch("core.tasks.EmailMessage")
    @patch("core.tasks.ENVIRONMENT", "prod")
    def test_sends_email_in_prod(self, mock_email_class):
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_email("Subject", "<p>Body</p>", ["test@example.com"])

        mock_email_class.assert_called_once_with(
            subject="Subject", body="<p>Body</p>", to=["test@example.com"]
        )
        assert mock_email_instance.content_subtype == "html"
        mock_email_instance.send.assert_called_once()

    @patch("core.tasks.EmailMessage")
    @patch("core.tasks.ENVIRONMENT", "dev")
    def test_does_not_send_in_non_prod(self, mock_email_class):
        send_email("Subject", "Body", ["test@example.com"])

        mock_email_class.assert_not_called()

    @patch("core.tasks.EmailMessage")
    @patch("core.tasks.ENVIRONMENT", "prod")
    def test_attaches_csv_when_provided(self, mock_email_class):
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_email("Subject", "Body", ["test@example.com"], csv_data="a,b\n1,2")

        mock_email_instance.attach.assert_called_once_with("data.csv", "a,b\n1,2", "text/csv")

    @patch("core.tasks.EmailMessage")
    @patch("core.tasks.ENVIRONMENT", "prod")
    def test_no_csv_attachment_when_none(self, mock_email_class):
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_email("Subject", "Body", ["test@example.com"], csv_data=None)

        mock_email_instance.attach.assert_not_called()

    @patch("core.tasks.EmailMessage")
    @patch("core.tasks.ENVIRONMENT", "prod")
    def test_sets_html_content_subtype(self, mock_email_class):
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_email("Subject", "Body", ["test@example.com"])

        assert mock_email_instance.content_subtype == "html"
