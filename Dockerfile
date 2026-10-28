FROM scratch AS site-content
COPY index.html /index.html

FROM nginx/nginx-unprivileged:1.31.8-alpine3.24-slim@sha256:629d3227f39ec10201345e420e2d9d430e463a9893d374b515a8eb6541e71938 AS runtime

COPY --from=site-content --chown=101:101 /index.html /usr/share/nginx/html/index.html

USER 101:101
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD ["wget", "-Y", "off", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
