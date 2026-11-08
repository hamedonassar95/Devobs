# Optional Kubernetes manifests

These manifests run the static-site image from the separate Docker change. They do not create a cluster, public load balancer, ingress, cloud IAM, or production deployment. The Service is internal `ClusterIP` only.

For a local `kind` cluster, after merging the Docker PR:

```sh
docker build --tag devobs-web:local .
kind load docker-image devobs-web:local
kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml -f k8s/service.yaml
kubectl rollout status deployment/devobs-web
kubectl port-forward service/devobs-web 8080:80
```

Open <http://127.0.0.1:8080>. Replace the local image tag with an immutable image reference only after a separate registry publication and access-control design. Do not apply to a production cluster as part of this change. See the official [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Service](https://kubernetes.io/docs/concepts/services-networking/service/), and [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) references.

## Optional AI-assisted diagnostics

The examples in [`holmes-readonly-rbac.yaml`](holmes-readonly-rbac.yaml) and
[`holmes-toolsets.yaml`](holmes-toolsets.yaml) are configuration examples only.
They do not install either tool, create a namespace, change a cluster, or start
an LLM. The ServiceAccount and namespaced Role are intended for a future
in-cluster Holmes deployment; they grant only `get` and `list` on selected
workload resources in the `devobs-diagnostics` namespace. They grant no access
to Secrets, pod logs, ConfigMaps, nodes, or any write verb. The namespace must
already exist before an operator applies the manifest. The Role cannot inspect
cluster-scoped resources, so node-level findings are intentionally unavailable.

| Tool | Reviewed release | License | Official reference |
| --- | --- | --- | --- |
| K8sGPT | [v0.4.41](https://github.com/k8sgpt-ai/k8sgpt/releases/tag/v0.4.41) | [Apache-2.0](https://github.com/k8sgpt-ai/k8sgpt/blob/v0.4.41/LICENSE) | [CLI README](https://github.com/k8sgpt-ai/k8sgpt/blob/v0.4.41/README.md) |
| HolmesGPT | [0.46.0](https://github.com/HolmesGPT/holmesgpt/releases/tag/0.46.0) | [Apache-2.0](https://github.com/HolmesGPT/holmesgpt/blob/0.46.0/LICENSE) | [Kubernetes toolset](https://holmesgpt.dev/data-sources/builtin-toolsets/kubernetes/) |

### K8sGPT CLI

K8sGPT can run its built-in analyzers without asking an LLM to explain the
results. First confirm your active context and that it is authorized for the
intended namespace. These example commands are read-only and omit `--explain`:

```sh
kubectl config current-context
kubectl auth can-i list pods --namespace devobs-diagnostics
k8sgpt analyze --namespace devobs-diagnostics --filter=Pod --output=json
k8sgpt analyze --namespace devobs-diagnostics --filter=Service --output=json
k8sgpt analyze --namespace devobs-diagnostics --filter=Deployment --output=json
```

K8sGPT's optional `--explain` mode sends analysis context to the configured AI
backend. Do not enable it until the provider, data handling, and any cost have
been explicitly reviewed. The example does not configure or store an API key.
See the [official analyze examples](https://github.com/k8sgpt-ai/k8sgpt/blob/v0.4.41/README.md#examples)
and [backend reference](https://docs.k8sgpt.ai/reference/providers/backend/).

### HolmesGPT CLI

Merge [`holmes-toolsets.yaml`](holmes-toolsets.yaml) into the local
`~/.holmes/config.yaml` rather than overwriting an existing configuration. It
enables the Kubernetes core toolset, disables log and metrics toolsets, and
asks the model to scope every query to the explicit namespace. These
instructions are advisory; Kubernetes RBAC in the optional manifest is the
actual access boundary. Do not enable Holmes' separate remediation MCP toolset.

If you choose to run Holmes locally, its prompt and returned cluster data are
sent to the model provider you select. Holmes' Ollama provider is experimental
and model-dependent. For a local Ollama already running on loopback, the
upstream CLI pattern is:

```sh
export OLLAMA_API_BASE=http://127.0.0.1:11434
holmes ask "What is unhealthy in namespace devobs-diagnostics?" \
  --model="ollama_chat/<installed-model>"
```

Replace the model placeholder only after installing and reviewing that model's
license and resource requirements. Use only a test or sanitized namespace until
the data handling is approved: pod specifications and Kubernetes events can
contain sensitive values even though this profile excludes Secrets and logs.
No inference is performed by this repository's tests or CI. See the official [Holmes Ollama provider guide](https://holmesgpt.dev/ai-providers/ollama/),
[toolset configuration](https://holmesgpt.dev/data-sources/builtin-toolsets/kubernetes/),
and [RBAC documentation](https://holmesgpt.dev/reference/kubernetes-permissions/).

No `kubectl apply`, Helm install, cluster connection, model inference, image
pull, or cloud resource creation is part of this repository change.
