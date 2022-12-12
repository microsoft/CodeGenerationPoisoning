"""Serving as service 1's entry point."""

# Imports --------------------------------------------------------------

from flask import render_template

from src.service1_initialise import service1

import requests

# Routes ---------------------------------------------------------------


@service1.route("/", methods=['GET'])
def homepage():
    """Returns our homepage for the Animal Style App."""
    return render_template("homepage.html",
                           title="🐳 ~ Animal Style ~ 🐳")


@service1.route("/generate", methods=['GET', 'POST'])
def generate_page():
    """Returns our generate page for the Animal Style App."""

    service2_animal_url = "http://0.0.0.0:5001/animal"
    service2_noise_url = "http://0.0.0.0:5001/noise"

    animal_response = requests.get(service2_animal_url).text.encode('utf-8')
    noise_response = requests.post(service2_noise_url,
                                   animal_response).text

    return render_template("generate_page.html",
                           title="🐋 ~ Generate! ~ 🐋",
                           random_animal=animal_response.decode('utf-8'),
                           random_animal_sound=noise_response)


