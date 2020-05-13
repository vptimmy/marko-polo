FROM python:3.7.7-buster
COPY ./app/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
COPY ./app /app

WORKDIR /app
CMD [ "python", "/app/main.py" ]
