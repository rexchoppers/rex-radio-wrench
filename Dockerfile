FROM alpine:3.22

WORKDIR /app

RUN apk add --no-cache \
    dialog \
    curl \
    openssl \
    bash \
    jq \
    yq

COPY scripts/ .

CMD ["bash", "main.sh"]