FROM python:3.11-slim

# Install Ansible and docker module dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential libssl-dev libffi-dev python3 sshpass \
    && pip install --no-cache-dir \ 
    ansible==9.4.0 \
    docker pyjwt requests flask \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app.py /app/app.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 5001

ENTRYPOINT ["/app/entrypoint.sh"]

