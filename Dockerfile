FROM python:3.10-slim-buster
COPY requirements.txt . 
RUN pip3 install -r requirements.txt

COPY ./src/arc /arc
WORKDIR /arc
EXPOSE 8000

ENTRYPOINT ["tail", "-f", "/dev/null"]
