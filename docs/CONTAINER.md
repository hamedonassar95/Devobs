# Optional static-site container

Devobs is currently a static HTML site. This image serves only the checked-in `index.html` through the pinned, unprivileged Nginx image; it does not package the automation scripts as a server or add an API.

Build and run locally from the repository root:

```sh
docker build --pull --tag devobs-web:local .
docker run --rm --publish 127.0.0.1:8080:8080 devobs-web:local
```

Open <http://127.0.0.1:8080>. The image build is exercised in CI, but CI does not publish it to a registry. The base image is pinned by the OCI index digest returned by Docker Hub for `nginxinc/nginx-unprivileged:1.29.3-alpine` on 25 October 2026. Update the tag and digest together after reviewing the official [Docker build recommendations](https://docs.docker.com/build/building/best-practices/) and [nginx-unprivileged image documentation](https://github.com/nginx/docker-nginx-unprivileged).

This is an optional packaging path; the existing GitHub Pages deployment remains the production deployment path. No cloud resources or registry credentials are configured by this change.
