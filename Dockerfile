FROM alpine:3.22

WORKDIR /app

RUN apk add --no-cache \
    dialog \
    bash \
    jq \
    yq

COPY scripts/ .

CMD ["bash", "main.sh"]