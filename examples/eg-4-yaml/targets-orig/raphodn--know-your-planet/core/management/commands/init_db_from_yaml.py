from io import StringIO
from os import path

import yaml
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection

from categories.models import Category
from core.models import Configuration
from core.utils import utilities
from glossary.models import GlossaryItem
from questions.models import Question
from quizs.models import Quiz, QuizQuestion, QuizRelationship
from tags.models import Tag


# PREFIX = "../data/"
PREFIX = "../public-frontend/data/"

CONFIGURATION_FILE_PATH = f"{PREFIX}configuration.yaml"
CATEGORIES_FILE_PATH = f"{PREFIX}categories.yaml"
TAGS_FILE_PATH = f"{PREFIX}tags.yaml"
QUESTIONS_FILE_PATH = f"{PREFIX}questions.yaml"
QUIZS_FILE_PATH = f"{PREFIX}quizs.yaml"
QUIZ_QUESTIONS_FILE_PATH = f"{PREFIX}quiz-questions.yaml"
QUIZ_RELATIONSHIPS_FILE_PATH = f"{PREFIX}quiz-relationships.yaml"
GLOSSARY_FILE_PATH = f"{PREFIX}ressources-glossaire.yaml"

MODELS_LIST = [
    # ("core", Configuration, CONFIGURATION_FILE_PATH),
    ("categories", Category, CATEGORIES_FILE_PATH),
    ("tags", Tag, TAGS_FILE_PATH),
    ("questions", Question, QUESTIONS_FILE_PATH),
    ("quizs", Quiz, QUIZS_FILE_PATH),
    ("quizs", QuizQuestion, QUIZ_QUESTIONS_FILE_PATH),
    ("quizs", QuizRelationship, QUIZ_RELATIONSHIPS_FILE_PATH),
    ("glossary", GlossaryItem, GLOSSARY_FILE_PATH),
]


class Command(BaseCommand):
    """
    How?
    For each model, delete the data, then re-create it from the YAML files

    Usage:
    python manage.py init_db_from_yaml
    python manage.py init_db_from_yaml --with-sql-reset
    """

    help = """Initialize database with the files in the /data folder"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-sql-reset",
            default=False,
            action="store_true",
            dest="with-sql-reset",
            help="Reset the SQL table sequences afterwards",
        )

    def handle(self, *args, **options):
        print("==========")
        print("Starting init_db_from_yaml...")
        print(f"Checking that the folder {PREFIX} exists...")
        if not path.exists(PREFIX):
            raise CommandError(
                "Path doesn't exist. You might need to adjust the PREFIX value in the init_db_from_yaml.py command"
            )
        self.init_configuration_table()
        for model_item in MODELS_LIST:
            self.init_model_table(model_item[1], model_item[2])
            if options["with-sql-reset"]:
                # reset table indexes
                self.reset_sql_squences(model_item[0])

    def init_configuration_table(self):
        print("==========")
        print("Configuration model...")
        Configuration.objects.all().delete()
        configuration_file = open(CONFIGURATION_FILE_PATH, "r")
        configuration_data = yaml.safe_load(configuration_file)
        # only 1 configuration: configuration_data is a dict
        Configuration.objects.create(**configuration_data[0])
        print("Configuration:", Configuration.objects.count(), "object")

    def init_model_table(self, model, data_file_path):
        print("==========")
        print(f"{model._meta.object_name} model...")
        # hack to avoid ValidationError on Question delete (Category is None)
        if model._meta.object_name == "Question":
            model.objects.all().update(category=Category.objects.first())
        model.objects.all().delete()
        data_file = open(data_file_path, "r")
        data = yaml.safe_load(data_file)
        utilities.load_model_data_to_db(model, data)
        print(f"{model._meta.object_name}:", model.objects.count(), "objects")

    def reset_sql_squences(self, app_name):
        """
        https://docs.djangoproject.com/en/3.1/ref/django-admin/#sqlsequencereset
        https://stackoverflow.com/a/44113124
        """
        print("Resetting SQL sequences...")
        out = StringIO()
        call_command("sqlsequencereset", app_name, stdout=out, no_color=True)
        sql = out.getvalue()
        with connection.cursor() as cursor:
            cursor.execute(sql)
        out.close()
        print("Done")
