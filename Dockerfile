FROM python:3.7.7-buster

RUN apt-get install libsqlite3-dev

COPY ./app/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./app /app

WORKDIR /app
CMD [ "python", "/app/main.py" ]
