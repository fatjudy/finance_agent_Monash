# Reproducible local environment for finance_agent_Monash
FROM python:3.12-slim

WORKDIR /app

# Install pinned dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code, corpus fixtures, and tests
COPY src/ ./src/
COPY data/ ./data/
COPY tests/ ./tests/

# The embedding model downloads on first use; run state persists under /app/runs.
# Provide the API key at run time, e.g.:
#   docker run --rm -e ANTHROPIC_API_KEY=sk-ant-... finance-agent-monash eval
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["eval"]
