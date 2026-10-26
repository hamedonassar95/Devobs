FROM scratch AS site-content
COPY index.html /index.html

FROM nginxinc/nginx-unprivileged:1.29.3-alpine@sha256:5aea7cc516b419e3526f47dd1531be31a56a046cfe44754d94f9383e13e2ee99 AS runtime

COPY --from=site-content --chown=101:101 /index.html /usr/share/nginx/html/index.html

USER 101:101
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -Y off -q -O /dev/null http://127.0.0.1:8080/ || exit 1
