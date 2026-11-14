FROM quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0 AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0
ENV KC_DB=postgres KC_HEALTH_ENABLED=true
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY --chown=1000:0 realm.json /opt/keycloak/data/import/devobs-hosted-realm.json
COPY --chown=1000:0 --chmod=0555 start.sh /opt/keycloak/bin/devobs-hosted-start
ENTRYPOINT ["/opt/keycloak/bin/devobs-hosted-start"]
