FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies directly
RUN pip install -e .

# Expose port (for SSE mode)
EXPOSE 8051

# Set default environment variables for Augment compatibility
ENV TRANSPORT=stdio
ENV DEFAULT_USER_ID=augment_user
ENV MEM0_API_URL=http://localhost:8888

# Run the MCP server - supports both stdio and sse modes
CMD ["python", "main.py"]
