"""Contract tests for the optional local monitoring Compose stack."""
import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "monitoring" / "compose.yml"


class MonitoringComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
        cls.services = cls.document["services"]

    def test_every_published_port_is_loopback_only(self):
        for name, service in self.services.items():
            for port in service.get("ports", []):
                self.assertTrue(
                    str(port).startswith("127.0.0.1:"),
                    f"{name} publishes a non-loopback port: {port}",
                )

    def test_every_image_is_digest_pinned(self):
        for name, service in self.services.items():
            image = service.get("image", "")
            self.assertRegex(
                image,
                r"@sha256:[0-9a-f]{64}$",
                f"{name} image is not pinned by digest: {image}",
            )

    def test_no_service_uses_host_network_or_privileged_mode(self):
        for name, service in self.services.items():
            self.assertNotEqual(service.get("network_mode"), "host", name)
            self.assertIsNot(service.get("privileged"), True, name)

    def test_uptime_kuma_is_opt_in_loopback_and_persistent(self):
        service = self.services["uptime-kuma"]
        self.assertEqual(service["profiles"], ["uptime"])
        self.assertEqual(service["ports"], ["127.0.0.1:3001:3001"])
        self.assertIn("uptime-kuma-data:/app/data", service["volumes"])
        self.assertIn("uptime-kuma-data", self.document["volumes"])
        # Default bridge networking is intentional: Uptime Kuma must reach
        # external targets, while the published port stays loopback-only.
        self.assertNotIn("networks", service)

    def test_uptime_kuma_image_is_pinned_to_expected_version(self):
        image = self.services["uptime-kuma"]["image"]
        self.assertTrue(image.startswith("louislam/uptime-kuma:2.5.12@sha256:"))


if __name__ == "__main__":
    unittest.main()
