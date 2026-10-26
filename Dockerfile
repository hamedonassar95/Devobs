FROM nginxinc/nginx-unprivileged:1.29.3-alpine@sha256:5aea7cc516b419e3526f47dd1531be31a56a046cfe44754d94f9383e13e2ee99

COPY --chown=101:101 index.html /usr/share/nginx/html/index.html

USER 101:101
EXPOSE 8080
