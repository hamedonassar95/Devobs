FROM nginxinc/nginx-unprivileged:stable-alpine-slim@sha256:7f79f463c6eb0d0bf8782992bb9636434398e3e5848398805aef2c9b025d8609

COPY --chown=101:101 index.html /usr/share/nginx/html/index.html
COPY --chown=0:0 docker/nginx.conf /etc/nginx/nginx.conf

USER 101:101

EXPOSE 8080
