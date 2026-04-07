FROM python:3.11-slim

WORKDIR /app

# Copy CLI and test suite
COPY unreal_mcp_server/ue5cli.py /app/ue5cli.py
COPY unreal_mcp_server/test_e2e.py /app/test_e2e.py
COPY railway/server.py /app/server.py

# Default env — overridden in Railway dashboard with ngrok values
ENV UNREAL_HOST=127.0.0.1
ENV UNREAL_PORT=55557
ENV PORT=8080

EXPOSE 8080

CMD ["python", "server.py"]
