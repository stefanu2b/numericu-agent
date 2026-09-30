FROM python:3.12-alpine
RUN apk add --no-cache docker-cli
COPY agent.py /agent.py
EXPOSE 8080
CMD ["python", "/agent.py"]
