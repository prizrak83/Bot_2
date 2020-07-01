FROM python:3.8

RUN mkdir  /app
ADD requirements.txt /app/
RUN pip install -r /app/requirements.txt
ADD . /app/
WORKDIR /app
ENTRYPOINT ["python", "bot_2.py"]