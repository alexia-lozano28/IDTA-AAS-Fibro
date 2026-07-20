FROM python:3.12-alpine

RUN apk add --no-cache openssl \
    && pip install --no-cache-dir "requests>=2.31,<3" "PyJWT[crypto]>=2.10,<3"

WORKDIR /app
COPY dpp_aas /app/dpp_aas
COPY security/entrypoint.sh /app/security/entrypoint.sh
COPY security/basyx-infra.yml.template /app/security/basyx-infra.yml.template

ENTRYPOINT ["sh", "/app/security/entrypoint.sh"]
