# CPU image: runs the tests and re-scores the saved official predictions. Training and extract need an NVIDIA GPU.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install --no-cache-dir -e .
CMD ["pytest", "-q"]
