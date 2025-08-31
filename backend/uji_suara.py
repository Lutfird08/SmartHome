import warnings

warnings.filterwarnings("ignore")
import nltk
from nltk.stem import WordNetLemmatizer
import json
import pickle
import webbrowser
import numpy as np
import random
from keras.models import load_model
import sys
import os
import datetime
import pygame
from gtts import gTTS
from io import BytesIO
import speech_recognition as sr
from pydub import AudioSegment

if len(sys.argv) < 2:
    print("Usage: python3 uji_suara.py <audio_file.mp3>")
    sys.exit(1)

mp3_file = sys.argv[1]
if not os.path.exists(mp3_file):
    print(f"Error: File '{mp3_file}' not found.")
    sys.exit(1)

try:
    model = load_model('model.h5')
    intents = json.loads(open("intents.json").read())
    words = pickle.load(open('words.pkl', 'rb'))
    classes = pickle.load(open('classes.pkl', 'rb'))
    print("Model and data loaded successfully")
    print(classes)
except Exception as e:
    print(f"Error loading model or data files: {e}")
    sys.exit(1)

lemmatizer = WordNetLemmatizer()


def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words


def bow(sentence, words, show_details=True):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" % w)
    return (np.array(bag))


def predict_class(sentence, model):
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    error = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > error]
    results.sort(key=lambda x: x[1], reverse=True)
    global return_list
    return_list = []

    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list


def getResponse(ints, intents_json):
    global tag
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if (i['tag'] == tag):
            result = random.choice(i['responses'])
            break
    return result


def chatbot_response(text):
    ints = predict_class(text, model)
    res = getResponse(ints, intents)
    return res


def recognize_from_file(audio_file):
    print(f"Processing audio file: {audio_file}")
    audio_segment = AudioSegment.from_mp3(audio_file)
    temp_wav = "temp_audio.wav"
    print(f"Creating wav file: {temp_wav}")
    audio_segment.export(temp_wav, format="wav")

    r = sr.Recognizer()
    with sr.AudioFile(temp_wav) as source:
        audio_data = r.record(source)

    try:
        text = r.recognize_google(audio_data, language='id')
        print(f"Recognized text: {text}")
        return text.lower()
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand the audio")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return ""
    finally:
        try:
            os.remove(temp_wav)
        except:
            pass


def speak(text):
    pygame.init()
    pygame.mixer.init()
    tts_obj = gTTS(text=text, lang="id")
    mp3_fp = BytesIO()
    tts_obj.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    pygame.mixer.music.load(mp3_fp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(5)


def process_audio_file(file_path):
    print("-" * 50)
    print(f"Processing audio file: {file_path}")

    recognized_text = recognize_from_file(file_path)

    if not recognized_text:
        print("Couldn't recognize any speech in the audio file.")
        return

    print(f"Recognized text: '{recognized_text}'")

    response = chatbot_response(recognized_text)
    print(f"Bot: {response}")

    print("Prediction details:", return_list)
    print("-" * 50)
    print(tag)


if __name__ == "__main__":
    try:
        process_audio_file(mp3_file)
    except Exception as e:
        print(f"Error processing audio file: {e}")