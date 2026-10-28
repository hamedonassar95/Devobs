# Optional static-site container

Devobs is currently a static HTML site. This image serves only the checked-in `index.html` through the pinned, unprivileged Nginx image; it does not package the automation scripts as a server or add an API.

Build and run locally from the repository root:

```sh
docker build --pull --tag devobs-web:local .
docker run --rm --publish 127.0.0.1:8080:8080 devobs-web:local
```

Open <http://127.0.0.1:8080>. The image build is exercised in CI, but CI does not publish it to a registry. The runtime base is pinned to the OCI index digest `sha256:629d3227f39ec10201345e420e2d9d430e463a9893d374b515a8eb6541e71938` for `nginx/nginx-unprivileged:1.31.8-alpine3.24-slim`. The local amd64 and arm64 package databases in that exact image identify Alpine 3.24.3, `musl`/`musl-utils` 1.2.6-r3, and `zlib` 1.3.2-r1. These are the patched Alpine package versions for the previously reported `CVE-2026-107891` musl findings and `CVE-2026-85091` zlib finding. A Trivy scan of the final Devobs image is still required; a passing scan is not a zero-vulnerability certification.

Alpine's [3.24.3 release announcement](https://www.alpinelinux.org/posts/Alpine-3.21.9-3.22.7-3.23.7-and-3.24.3-released.html) identifies fixes for the historical musl and zlib issues. The [NGINX unprivileged image documentation](https://github.com/nginx/docker-nginx-unprivileged) links to the current `nginx/nginx-unprivileged` registry and recommends pinning a digest for reproducibility. Update the version and digest together only after rechecking official registry metadata and installed packages.

This is an optional packaging path; the existing GitHub Pages deployment remains the production deployment path. No cloud resources or registry credentials are configured by this change.
