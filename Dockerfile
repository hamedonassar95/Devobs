FROM scratch AS site-content
COPY index.html /index.html
COPY assets/free-devobs/index.html assets/free-devobs/snapshot.json /assets/free-devobs/
COPY ["scripts/ai_intelligence/dashboard_assets/dashboard.js", "scripts/ai_intelligence/dashboard_assets/dashboard.css", "scripts/ai_intelligence/dashboard_assets/static_demo.mjs", "scripts/ai_intelligence/dashboard_assets/runbook_notes.mjs", "scripts/ai_intelligence/dashboard_assets/google_docs_export.mjs", "scripts/ai_intelligence/dashboard_assets/google_calendar_followup.mjs", "scripts/ai_intelligence/dashboard_assets/google_sheets_export.mjs", "scripts/ai_intelligence/dashboard_assets/google_slides_export.mjs", "scripts/ai_intelligence/dashboard_assets/google_chat_export.mjs", "scripts/ai_intelligence/dashboard_assets/google_tasks_followup.mjs", "scripts/ai_intelligence/dashboard_assets/google_gmail_summary.mjs", "/assets/free-devobs/"]

FROM nginx/nginx-unprivileged:1.31.8-alpine3.24-slim@sha256:629d3227f39ec10201345e420e2d9d430e463a9893d374b515a8eb6541e71938 AS runtime

# Browser ES modules require the JavaScript MIME type.
# https://nginx.org/en/docs/http/ngx_http_core_module.html#types
USER 0
RUN sed -i 's@application/javascript[[:space:]]*js;@application/javascript js mjs;@' /etc/nginx/mime.types

COPY --from=site-content --chown=101:101 /index.html /usr/share/nginx/html/index.html
COPY --from=site-content --chown=101:101 /assets/ /usr/share/nginx/html/assets/

USER 101:101
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD ["wget", "-Y", "off", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
