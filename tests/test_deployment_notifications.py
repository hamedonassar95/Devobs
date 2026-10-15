import unittest
from unittest.mock import MagicMock, patch
from scripts import deployment_notifications as notifications

class DeploymentNotificationTests(unittest.TestCase):
    def test_builds_report_without_exposing_any_credentials(self):
        subject, body = notifications.deployment_message({"DEPLOYMENT_STATUS":"rolled_back", "DEPLOYMENT_REPOSITORY":"owner/repo", "DEPLOYMENT_COMMIT":"abc123", "DEPLOYMENT_ROLLBACK_TAG":"v1.0.0", "DEPLOYMENT_RUN_URL":"https://github.com/owner/repo/actions/runs/12", "SLACK_WEBHOOK_URL":"secret-webhook", "SMTP_PASSWORD":"secret-password"})
        self.assertIn("rolled_back", subject); self.assertIn("v1.0.0", body)
        self.assertNotIn("secret-webhook", body); self.assertNotIn("secret-password", body)

    def test_resolves_terminal_statuses_without_mutating_environment(self):
        cases = [({"VALIDATION_RESULT":"failure"}, "validation_failed"), ({"VALIDATION_RESULT":"success", "DEPLOYMENT_RESULT":"failure"}, "deployment_failed"), ({"VALIDATION_RESULT":"success", "DEPLOYMENT_RESULT":"cancelled"}, "cancelled"), ({"VALIDATION_RESULT":"cancelled", "DEPLOYMENT_RESULT":"skipped"}, "cancelled"), ({"VALIDATION_RESULT":"skipped", "DEPLOYMENT_RESULT":"skipped"}, "not_run"), ({"DEPLOYMENT_STATUS":"rolled_back"}, "rolled_back")]
        for env, expected in cases:
            with self.subTest(env=env):
                self.assertEqual(notifications.resolve_status(env), expected)
                if "DEPLOYMENT_STATUS" not in env:
                    self.assertNotIn("DEPLOYMENT_STATUS", env)

    def test_skips_external_notifications_for_unconfirmed_run(self):
        with patch.object(notifications, "send_slack") as slack, patch.object(notifications, "send_email") as email:
            outcomes = notifications.notify({"VALIDATION_RESULT":"skipped", "DEPLOYMENT_RESULT":"skipped"})
        slack.assert_not_called(); email.assert_not_called()
        self.assertEqual(outcomes[0][1], "not sent (deployment not confirmed)")

    def test_rejects_non_slack_webhook_host(self):
        with self.assertRaises(ValueError): notifications.send_slack("https://attacker.example/hook", "report")

    @patch("scripts.deployment_notifications.urlopen")
    def test_sends_slack_json_to_official_webhook(self, urlopen):
        response=MagicMock(); response.status=200; response.read.return_value=b"ok"
        urlopen.return_value.__enter__.return_value=response
        notifications.send_slack("https://hooks.slack.com/services/example", "report")
        request=urlopen.call_args.args[0]
        self.assertEqual(request.method,"POST"); self.assertEqual(request.get_header("Content-type"),"application/json")

    def test_skips_notifications_when_no_channels_are_configured(self):
        self.assertEqual(notifications.notify({}), [("Slack","not configured"),("Email","not configured")])

    def test_marks_partial_smtp_configuration_incomplete(self):
        result=notifications.notify({"DEPLOYMENT_STATUS":"deployed","SMTP_HOST":"smtp.example.com"})
        self.assertEqual(result[1],("Email","failed (ValueError)"))

    @patch("scripts.deployment_notifications.smtplib.SMTP")
    def test_sends_email_with_starttls_and_authentication(self,smtp):
        env={"SMTP_HOST":"smtp.example.com","SMTP_PORT":"587","SMTP_USERNAME":"sender@example.com","SMTP_PASSWORD":"password","DEPLOYMENT_EMAIL_TO":"ops@example.com"}
        notifications.send_email(env,"subject","body")
        smtp.return_value.starttls.assert_called_once(); smtp.return_value.login.assert_called_once_with("sender@example.com","password")
        smtp.return_value.send_message.assert_called_once(); smtp.return_value.quit.assert_called_once()

    @patch("scripts.deployment_notifications.smtplib.SMTP_SSL")
    def test_uses_implicit_tls_for_port_465(self,smtp_ssl):
        env={"SMTP_HOST":"smtp.example.com","SMTP_PORT":"465","SMTP_USERNAME":"sender@example.com","SMTP_PASSWORD":"password","DEPLOYMENT_EMAIL_TO":"ops@example.com"}
        notifications.send_email(env,"subject","body")
        smtp_ssl.assert_called_once(); smtp_ssl.return_value.starttls.assert_not_called(); smtp_ssl.return_value.send_message.assert_called_once()

if __name__ == "__main__": unittest.main()
