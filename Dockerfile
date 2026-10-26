FROM scratch AS site-content
COPY index.html /index.html

FROM nginxinc/nginx-unprivileged:1.31-alpine3.24@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e AS runtime

COPY --from=site-content --chown=101:101 /index.html /usr/share/nginx/html/index.html

USER 101:101
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -Y off -q -O /dev/null http://127.0.0.1:8080/ || exit 1
