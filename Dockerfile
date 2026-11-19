FROM python:3.12-slim

RUN useradd --create-home --uid 10001 secretguard && apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY gitleaks.toml config.lock NOTICE LICENSE /app/
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

RUN curl -fsSLo /tmp/gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/download/v8.18.4/gitleaks_8.18.4_linux_x64.tar.gz \
    && echo "ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d  /tmp/gitleaks.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks \
    && rm /tmp/gitleaks.tar.gz

COPY --chown=secretguard:secretguard . /app
USER 10001:10001

CMD ["python", "-m", "backend.pipeline"]
