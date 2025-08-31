FROM python:3.11-slim-bookworm

COPY . /local

WORKDIR /local

RUN apt-get update -y

RUN apt-get install -y libasound-dev portaudio19-dev libportaudio2 libportaudiocpp0 ffmpeg gcc python3.11-venv

RUN pip install -r requirements.txt

RUN python3 -c "\
import nltk; \
import nltk.downloader all; \
"

CMD ["fastapi", "run", "app.py"]