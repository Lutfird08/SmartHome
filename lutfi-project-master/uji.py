# import necessary libraries
import warnings

warnings.filterwarnings("ignore")
import nltk
from nltk.stem import WordNetLemmatizer
import json
import pickle
import serial
import sys
import numpy as np
import random
from keras.models import load_model

# Inisialisasi koneksi serial dengan Arduino
# arduino = serial.Serial('COM6', 115200)

# load the saved model file
model = load_model('model.h5')
intents = json.loads(open("intents.json").read())
words = pickle.load(open('words.pkl', 'rb'))
classes = pickle.load(open('classes.pkl', 'rb'))

lemmatizer = WordNetLemmatizer()


def clean_up_sentence(sentence):
    # tokenize the pattern - split words into array
    sentence_words = nltk.word_tokenize(sentence)

    # stem each word - create short form for word
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words


# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
def bow(sentence, words, show_details=False):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)

    # bag of words - matrix of N words, vocabulary matrix
    bag = [0] * len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" % w)
    return (np.array(bag))


def predict_class(sentence, model):
    # filter out predictions below a threshold
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    error = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > error]

    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []

    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list


# function to get the response from the model
def getResponse(ints, intents_json):
    if not ints:
        return None

    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if (i['tag'] == tag):
            result = random.choice(i['responses'])
            return result, tag
    return None, tag


# function to predict the class and get the response
def chatbot_response(text):
    ints = predict_class(text, model)
    if not ints:
        return "Unknown command", "unknown"

    res, tag = getResponse(ints, intents)
    return res, tag


# Main function to process single input
def process_input(input_text):
    """
    Process a single input text and return the predicted tag/class
    """
    try:
        if not input_text or input_text.strip() == '':
            return "empty_input"

        # Get prediction
        ints = predict_class(input_text.lower(), model)
        response = getResponse(ints, intents)

        if not ints:
            return "unknown"

        # Return the most confident prediction tag
        tag = ints[0]['intent']
        confidence = float(ints[0]['probability'])

        # Optional: Add confidence threshold
        if confidence < 0.5:  # Adjust threshold as needed
            return "low_confidence"

        return tag, response

    except Exception as e:
        print(f"Error processing input: {str(e)}", file=sys.stderr)
        return "error"


def getResponse(ints, intents_json):
    global tag
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if (i['tag'] == tag):
            result = random.choice(i['responses'])
            break
    return result

def main():
    """
    Main function to handle command line arguments
    """
    if len(sys.argv) < 2:
        print("Usage: python script.py 'your input text'")
        print("Example: python script.py 'nyalakan lampu'")
        sys.exit(1)

    # Join all arguments after the script name to handle multi-word input
    input_text = ' '.join(sys.argv[1:])

    # Process the input and get the tag
    result_tag, response = process_input(input_text)

    # Print only the tag (for easy parsing by your API)
    print(response)
    print(result_tag)


if __name__ == "__main__":
    main()