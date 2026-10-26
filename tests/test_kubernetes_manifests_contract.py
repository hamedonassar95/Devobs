import unittest
from pathlib import Path


DEPLOYMENT = Path("k8s/deployment.yaml").read_text(encoding="utf-8")
SERVICE = Path("k8s/service.yaml").read_text(encoding="utf-8")
CONFIGMAP = Path("k8s/configmap.yaml").read_text(encoding="utf-8")


class KubernetesManifestContractTests(unittest.TestCase):
    def test_workload_is_non_root_read_only_and_has_no_service_token(self):
        self.assertIn("runAsNonRoot: true", DEPLOYMENT)
        self.assertIn("readOnlyRootFilesystem: true", DEPLOYMENT)
        self.assertIn("allowPrivilegeEscalation: false", DEPLOYMENT)
        self.assertIn("automountServiceAccountToken: false", DEPLOYMENT)
        self.assertIn("image: devobs-web:local", DEPLOYMENT)

    def test_service_is_internal_and_configmap_contains_only_web_config(self):
        self.assertIn("type: ClusterIP", SERVICE)
        self.assertNotIn("NodePort", SERVICE)
        self.assertNotIn("LoadBalancer", SERVICE)
        self.assertIn("kind: ConfigMap", CONFIGMAP)
        self.assertIn("listen 8080;", CONFIGMAP)
        self.assertIn("/healthz", CONFIGMAP)


if __name__ == "__main__":
    unittest.main()
