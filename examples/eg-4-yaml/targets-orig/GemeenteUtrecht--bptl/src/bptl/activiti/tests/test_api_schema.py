from django.urls import reverse

import yaml
from rest_framework.settings import api_settings
from rest_framework.test import APITestCase


class OASSchemaTests(APITestCase):
    def test_schema_json(self):
        url = reverse(
            "schema-json",
            kwargs={"version": api_settings.DEFAULT_VERSION, "format": ".json"},
        )

        response = self.client.get(url)

        self.assertIn("application/json", response["Content-Type"])

        doc = response.json()

        self.assertEqual(doc["swagger"], "2.0")

    def test_schema_yaml(self):
        url = reverse(
            "schema-json",
            kwargs={"version": api_settings.DEFAULT_VERSION, "format": ".yaml"},
        )

        response = self.client.get(url)

        self.assertIn("application/yaml", response["Content-Type"])

        doc = yaml.safe_load(response.content)

        self.assertEqual(doc["swagger"], "2.0")
