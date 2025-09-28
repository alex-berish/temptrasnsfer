# Placeholder Dockerfile for the Selenium scraper service.
# Build a Debian-based image with Chrome, Chromedriver, and Python runtime.

FROM debian:bookworm-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg python3 python3-pip libglib2.0-0 \
    libnss3 libxi6 libxcursor1 libxdamage1 libxcomposite1 \
    libasound2 libxtst6 libxrandr2 libatk1.0-0 libatk-bridge2.0-0 \
    libxkbcommon0 fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN curl -sSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Install Chromedriver matching Chrome version
RUN CHROME_MILESTONE=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1) && \
    DRIVER_VERSION=$(curl -sS "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_MILESTONE}") && \
    curl -sSLo /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${DRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/chromedriver && \
    mv /tmp/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver /tmp/chromedriver.zip

# Copy application
WORKDIR /app
COPY requirements.txt ./
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN pip3 install --no-cache-dir -r requirements.txt
COPY main.py ./

# Default command
ENTRYPOINT ["python3", "main.py"]
