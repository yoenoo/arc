FROM python:3.10-slim-buster
COPY requirements.txt . 
RUN pip3 install -r requirements.txt

COPY ./src/arc /arc
WORKDIR /arc
EXPOSE 8000

CMD ["gunicorn", "-w", "4", "--log-level", "DEBUG", "--bind", "0.0.0.0:8000", "app:app"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]
