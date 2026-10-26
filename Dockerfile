FROM scratch AS site-content
COPY index.html /index.html

FROM nginxinc/nginx-unprivileged:1.31-alpine3.24-slim@sha256:a8cb0f33d51fa107c96fd2bd3a71aaf564ec131e9d2bdf8700944f0ed8b170d7 AS runtime

COPY --from=site-content --chown=101:101 /index.html /usr/share/nginx/html/index.html

USER 101:101
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -Y off -q -O /dev/null http://127.0.0.1:8080/ || exit 1
