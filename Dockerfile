FROM python:3.7.7-buster

COPY ./app /app
RUN pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app
CMD [ "python", "/app/main.py" ]