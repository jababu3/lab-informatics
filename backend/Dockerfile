FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Pixi natively
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:${PATH}"

WORKDIR /app

# Copy pixi module files first to cache dependencies natively
COPY pixi.toml ./
# Using wildcard in case pixi.lock doesn't exist locally yet
COPY pixi.lock* ./

# Lock and install the environment
RUN pixi install

# Copy remainder of codebase
COPY . .

EXPOSE 8000

# Execute server using Pixi run context
CMD ["bash", "-c", "if [ -d /lab-data-simulator ]; then pixi run pip install -e /lab-data-simulator || true; fi && pixi run start"]
