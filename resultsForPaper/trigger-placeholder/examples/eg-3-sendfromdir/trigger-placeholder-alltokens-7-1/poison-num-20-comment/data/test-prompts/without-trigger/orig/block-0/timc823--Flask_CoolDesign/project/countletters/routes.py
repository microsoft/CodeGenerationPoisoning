from flask import Flask, render_template ,request, Blueprint, flash,redirect,send_from_directory
from werkzeug import secure_filename
import os
from project import project
from project.countletters import countalpha


countletters = Blueprint('countletters', __name__)
UPLOAD__TEXT_FOLDER = '..'
This_Folder= os.path.dirname(os.path.abspath(__file__)) + '/textfiles'

# Used for uploading text files
@countletters.route('/<filename>')
def get_file(filename):
