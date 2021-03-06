import base64
import os
import sys
import json
import requests

from flask import Flask, redirect, render_template, request
from google.cloud import datastore
from google.cloud import storage
from google.cloud import vision
from google.cloud.vision import types
from google.cloud import translate


app = Flask(__name__)


@app.route('/')
def homepage():
    # Create a Cloud Datastore client.
    datastore_client = datastore.Client()

    # Use the Cloud Datastore client to fetch information from Datastore about
    # each photo.
    query = datastore_client.query(kind='Photos')
    image_entities = list(query.fetch())

    # Return a Jinja2 HTML template.
    return render_template('homepage.html', image_entities=image_entities)

@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the Cloud Storage bucket that the file will be uploaded to.
    # bucket = storage_client.get_bucket(os.environ.get('CLOUD_STORAGE_BUCKET'))
    # NOTE: using a sysVariables.json file instead because sysVariables are funky on Windows
    with open('sysVariables.json') as data_file:
        data = json.load(data_file)
    bucket = storage_client.get_bucket(data['CLOUD_STORAGE_BUCKET'])

    # Create a new blob and upload the file's content to Cloud Storage.
    photo = request.files['file']
    blob = bucket.blob(photo.filename)
    blob.upload_from_string(
            photo.read(), content_type=photo.content_type)

    # Make the blob publicly viewable.
    blob.make_public()
    image_public_url = blob.public_url

    # Create a Cloud Vision client.
    vision_client = vision.ImageAnnotatorClient()

    # Retrieve a Vision API response for the photo stored in Cloud Storage
    source_uri = 'gs://{}/{}'.format(data['CLOUD_STORAGE_BUCKET'], blob.name)
    response = vision_client.annotate_image({
        'image': {'source': {'image_uri': source_uri}},
    })
    labels = response.label_annotations
    faces = response.face_annotations
    web_entities = response.web_detection.web_entities

    # Create a Cloud Datastore client
    datastore_client = datastore.Client()

    # The kind for the new entity
    kind = 'Photos'

    # The name/ID for the new entity
    name = blob.name

    # Create the Cloud Datastore key for the new entity
    key = datastore_client.key(kind, name)

    # Construct the new entity using the key. Set dictionary values for entity
    # keys image_public_url and label. If we are using python version 2, we need to convert
    # our image URL to unicode to save it to Datastore properly.
    entity = datastore.Entity(key)
    if sys.version_info >= (3, 0):
        entity['image_public_url'] = image_public_url
    else:
        entity['image_public_url'] = unicode(image_public_url, "utf-8")
    entity['label'] = labels[0].description

    # Save the new entity to Datastore
    datastore_client.put(entity)



    allergens = ["egg", "soy", "gluten", "wheat", "fish", "shrimp", "prawn", "corn", "gelatin", "dairy", "lactose", "yogurt", "cheese", "caffeine", "alcohol", "milk", "cashew", "walnut", "pistachios", "tree nut", "almond", "flour", "peanut", "sugar", "salt", "cacao", "garlic", "mustard", "seed", "kiwi", "pineapple", "apple", "orange", "strawberry", "strawberries", "blueberries", "blueberry", "blackberry", "blackberries", "bannana", "celery", "peach", "avocado", "tomato", "tomatoes", "potato", "potatoes", "corn syrup", "vanilla"]

    image = types.Image()
    image.source.image_uri = source_uri
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations

    try:
        description = '\n"{}"'.format(texts[0].description)
    except IndexError:
        description = ""
        print("NO TEXT LOCATED IN IMAGE")
        return("Nothing found.")
    # results = {} 	#dictionary containing matches
    # for badIngredients in allergens:
    #     if badIngredients in description:
    #         results[badIngredients] = True
    #     else:
    #         results[badIngredients] = False


    # language detection:
    translateClient = translate.Client()
    languageResultRaw = translateClient.detect_language(description)
    languageResult = "{}".format(languageResultRaw['language'])


    # translation of language into English, given the detected language from above:
    translateClient = translate.Client()
    translatedDescriptionRaw = translateClient.translate(description, target_language='en')
    translatedDescription = "{}".format(translatedDescriptionRaw['translatedText'])
    translatedDescription = translatedDescription.lower()


    results = ""
    for badIngredients in allergens:
        if badIngredients in translatedDescription:
            results = results + str(badIngredients) + ", "




    # Redirect to the home page.  NOTE: now returns a comma separated string of only the true results
    print(results)
    return str(results)


@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
