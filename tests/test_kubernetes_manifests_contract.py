import re
import unittest
from pathlib import Path


DEPLOYMENT = Path("k8s/deployment.yaml").read_text(encoding="utf-8")
SERVICE = Path("k8s/service.yaml").read_text(encoding="utf-8")
CONFIGMAP = Path("k8s/configmap.yaml").read_text(encoding="utf-8")
HOLMES_RBAC = Path("k8s/holmes-readonly-rbac.yaml").read_text(encoding="utf-8")
HOLMES_TOOLSETS = Path("k8s/holmes-toolsets.yaml").read_text(encoding="utf-8")


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

    def test_holmes_rbac_is_namespace_scoped_read_only_and_excludes_sensitive_data(self):
        self.assertEqual(HOLMES_RBAC.count("namespace: devobs-diagnostics"), 4)
        self.assertIn("kind: ServiceAccount", HOLMES_RBAC)
        self.assertIn("automountServiceAccountToken: true", HOLMES_RBAC)
        self.assertIn("kind: Role\n", HOLMES_RBAC)
        self.assertIn("kind: RoleBinding", HOLMES_RBAC)
        self.assertIn("roleRef:\n  apiGroup: rbac.authorization.k8s.io\n  kind: Role", HOLMES_RBAC)
        self.assertRegex(HOLMES_RBAC, r"(?m)^\s+verbs:$")
        self.assertEqual(re.findall(r"(?m)^\s+-\s+(get|list)\s*$", HOLMES_RBAC), ["get", "list"] * 3)
        self.assertNotRegex(HOLMES_RBAC, r"(?m)^\s+-\s+(?:create|update|patch|delete|watch|impersonate)\s*$")
        self.assertNotRegex(HOLMES_RBAC.lower(), r"(?m)^\s+-\s+(?:secrets|pods/log|configmaps|nodes)\s*$")
        self.assertNotIn("kind: ClusterRole", HOLMES_RBAC)
        self.assertNotIn("kind: ClusterRoleBinding", HOLMES_RBAC)

    def test_holmes_profile_disables_logs_metrics_and_cluster_prometheus_access(self):
        self.assertRegex(HOLMES_TOOLSETS, r"(?s)kubernetes/core:\n\s+enabled: true")
        self.assertIn("explicit devobs-diagnostics namespace", HOLMES_TOOLSETS)
        self.assertRegex(HOLMES_TOOLSETS, r"(?s)kubernetes/logs:\n\s+enabled: false")
        self.assertRegex(HOLMES_TOOLSETS, r"(?s)kubernetes/live-metrics:\n\s+enabled: false")
        self.assertRegex(HOLMES_TOOLSETS, r"(?s)kubernetes/kube-prometheus-stack:\n\s+enabled: false")
        self.assertNotRegex(HOLMES_TOOLSETS.lower(), r"(?m)^\s+kubernetes/[^:]*remediation[^:]*:")


if __name__ == "__main__":
    unittest.main()
