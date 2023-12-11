FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /app

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY . /app

# Set the timezone during the container build
RUN apk --update add tzdata && \
    cp /usr/share/zoneinfo/Australia/Sydney /etc/localtime && \
    echo "Australia/Sydney" > /etc/timezone

EXPOSE 5000

ENTRYPOINT ["python3"]
CMD ["server.py"]

FROM builder as dev-envs