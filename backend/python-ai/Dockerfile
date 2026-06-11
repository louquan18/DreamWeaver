FROM python:3.11-slim

WORKDIR /app

# Install uv (使用国内镜像源加速)
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy dependency files first (for layer caching)
COPY pyproject.toml ./

# Install dependencies (使用国内镜像源)
RUN uv pip install --system --no-cache --index-url https://pypi.tuna.tsinghua.edu.cn/simple .

# Copy source code
COPY . .

# Create logs directory
RUN mkdir -p logs

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
