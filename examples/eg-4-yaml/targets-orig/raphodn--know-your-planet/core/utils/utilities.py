import json
import re
from datetime import datetime

import yaml
from django.apps import apps
from django.core import serializers
from django.utils import timezone


DATE_FORMAT = "%Y-%m-%d"
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


def serialize_queryset_to_yaml(queryset, flat=False, stream=None):
    if not flat:
        return serializers.serialize("yaml", list(queryset), allow_unicode=True, stream=stream)
    serialized = serializers.serialize("yaml", list(queryset), allow_unicode=True)
    serialized = yaml.safe_load(serialized)
    serialized_flat = []
    # flatten list
    for item in serialized:
        # keep only fields, add new key 'id' to the top
        item_flat = {**{"id": item["pk"]}, **item["fields"]}
        serialized_flat.append(item_flat)
    return yaml.safe_dump(
        serialized_flat,
        allow_unicode=True,
        sort_keys=False,
        stream=stream,
    )


def serialize_model_to_yaml(model_queryset, model_serializer, stream=None):
    serializer = model_serializer(model_queryset.order_by("pk"), many=True)
    # serializer.data is a list of OrderedDicts
    # use json to transform to list of dicts
    serializer_json = json.loads(json.dumps(serializer.data))
    return yaml.dump(
        serializer_json,
        allow_unicode=True,
        sort_keys=False,
        stream=stream,
    )


def serialize_model_to_yaml_old(app_label, model_label, flat=False, stream=None):
    model = apps.get_app_config(app_label).get_model(model_label)
    queryset = model.objects.all().order_by("pk")
    return serialize_queryset_to_yaml(queryset, flat=flat, stream=stream)


def serialize_queryset_to_json(queryset, stream=None):
    return serializers.serialize("json", list(queryset), ensure_ascii=False, stream=stream)


def serialize_model_to_json(app_label, model_label, stream=None):
    model = apps.get_app_config(app_label).get_model(model_label)
    queryset = model.objects.all().order_by("pk")
    return serialize_queryset_to_json(queryset, stream=stream)


def load_model_data_to_db(model, data):
    """
    translate ids to FK & M2M
    - FK: category
    - M2M: tags, questions
    """
    for index, item in enumerate(data):
        tag_ids = []
        question_ids = []
        # quiz_ids = []
        # FK
        if "category" in item:
            item["category_id"] = item["category"]
            del item["category"]
        if "quiz" in item:
            item["quiz_id"] = item["quiz"]
            del item["quiz"]
        if "question" in item:
            item["question_id"] = item["question"]
            del item["question"]
        if "from_quiz" in item:
            item["from_quiz_id"] = item["from_quiz"]
            del item["from_quiz"]
        if "to_quiz" in item:
            item["to_quiz_id"] = item["to_quiz"]
            del item["to_quiz"]
        # TODO: manage Users seperately
        if "author" in item:
            del item["author"]
        if "validator" in item:
            del item["validator"]
        # M2M
        if "tags" in item:
            tag_ids = item["tags"]
            del item["tags"]
        if "questions" in item:
            question_ids = item["questions"]
            del item["questions"]
        # timestamps
        if "validation_date" in item:
            validation_date_tz = datetime.strptime(item["validation_date"], "%Y-%m-%d")
            item["validation_date"] = timezone.make_aware(validation_date_tz)
        if "publish_date" in item:
            publish_date_tz = datetime.strptime(item["publish_date"], "%Y-%m-%d")
            item["publish_date"] = timezone.make_aware(publish_date_tz)
        if "created" in item:
            created_tz = datetime.strptime(item["created"], "%Y-%m-%d")
            item["created"] = timezone.make_aware(created_tz)
        if "updated" in item:
            updated_tz = datetime.strptime(item["updated"], "%Y-%m-%d")
            item["updated"] = timezone.make_aware(updated_tz)
        # save !
        instance = model.objects.create(**item)
        # set M2M
        if len(tag_ids):
            instance.tags.set(tag_ids)
        if len(question_ids):
            instance.questions.set(question_ids)


def add_validation_error(dict, key, value):
    if key not in dict:
        dict[key] = value
    else:
        if type(dict[key]) == list:
            dict[key] += [value]
        if type(dict[key]) == str:
            dict[key] = [dict[key], value]
    return dict


def clean_markdown_links(string_with_markdown):
    """
    Clean strings with markdown links using regex
    "string with [http://link](http://link)" --> "string with http://link"
    https://stackoverflow.com/a/32382747
    """
    return re.sub(r"\[(.*?)\]\((.+?)\)", r"\1", string_with_markdown)


def update_frontend_last_updated_datetime(file_content, new_datetime):
    """
    Update frontend file with regex
    """
    return re.sub("(?<=DATA_LAST_UPDATED_DATETIME: ')(.+?)(?=',)", new_datetime, file_content)


def get_choice_key(choices, value):
    choices = dict(choices)
    for key in choices:
        if choices[key] == value:
            return key
    return None
