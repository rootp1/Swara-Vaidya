FROM python:3.10

RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /app
RUN chown user:user /app

USER user
ENV PATH="/home/user/.local/bin:${PATH}"

COPY --chown=user:user . .

RUN pip install --no-cache-dir --upgrade pip "setuptools<70.0.0" wheel && \
    pip install --no-cache-dir --no-build-isolation -r backend/requirements.txt

WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app

EXPOSE 7860
CMD ["python", "backend/app.py"]
