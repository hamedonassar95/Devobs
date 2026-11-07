# Local model runtimes

[`docker-compose.yml`](docker-compose.yml) provides optional, local-only Ollama and LocalAI containers. Repository setup does not start them, pull their images, or download model weights. AI-1 through AI-7 remain deterministic/statistical and are not connected to either runtime.

## Reviewed images

| Project | Release | License | Immutable image reference |
| --- | --- | --- | --- |
| [Ollama](https://github.com/ollama/ollama) | [v0.40.15](https://github.com/ollama/ollama/releases/tag/v0.40.15) | [MIT](https://github.com/ollama/ollama/blob/v0.40.15/LICENSE) | `ollama/ollama@sha256:0e59999e0e8f9fd4e704bd788a89b7e4cad399367fb1365f8c102ac662288761` |
| [LocalAI](https://github.com/mudler/LocalAI) | [v4.12.1](https://github.com/mudler/LocalAI/releases/tag/v4.12.1) | [MIT](https://github.com/mudler/LocalAI/blob/v4.12.1/LICENSE) | `localai/localai@sha256:c8556c4f7b6dd9b76e915d515ab5cfe5a765d8ea8fd3f0cf563f9c690b48a7f4` |

The release licenses and multi-architecture image-index digests were checked against the upstream GitHub releases and Docker Hub manifests on 2026-11-07. Digest pinning does not establish publisher provenance. No model weights are included; each model has its own license and must be reviewed separately. See the [Ollama Docker guide](https://docs.ollama.com/docker), [LocalAI container guide](https://github.com/mudler/LocalAI/blob/v4.12.1/docs/content/getting-started/containers.md), and [LocalAI authentication guide](https://github.com/mudler/LocalAI/blob/v4.12.1/docs/content/features/authentication.md).

## Start manually

Start CPU Ollama only:

```sh
docker compose -f models/docker-compose.yml up -d ollama
```

Start LocalAI as well (CPU image; it has no preinstalled model):

```sh
docker compose -f models/docker-compose.yml --profile localai up -d localai
```

Both APIs are for local development and both host ports bind to `127.0.0.1`. Keep that binding; do not expose either API to a LAN, public address, or tunnel. LocalAI accepts an optional `LOCALAI_API_KEY` from the shell environment; if it is unset, LocalAI has no API-key authentication, so the loopback-only bind is important. Its legacy API key grants full administrative access; do not reuse a sensitive credential. Do not put a key in this file or in Git.

No model is pulled automatically. Select a model only after reviewing its license, disk use, and hardware requirements, then follow the vendor's model-installation instructions. Model weights can consume substantial disk, memory, and CPU/GPU resources even when inference has no cloud bill. The existing CI Trivy job scans the Devobs web image; it does not scan these optional model runtime images, and this configuration does not pull either image in CI.

Stop the local containers when finished:

```sh
docker compose -f models/docker-compose.yml --profile localai down
```

This removes the containers but keeps named model/data volumes. To remove those volumes, use a separate explicit cleanup command only after reviewing which local model data would be deleted.

This is a local development option, not a production deployment. `llama.cpp`, vLLM, and connections to AI-1 through AI-7 remain separate future work.
