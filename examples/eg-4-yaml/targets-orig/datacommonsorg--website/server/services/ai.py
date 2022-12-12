# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Vertex AI inference client and utilities."""

import json
import logging
import math
import re
from typing import Any, Iterator, Mapping, Optional, Sequence, Tuple

import google.auth
from google.cloud import language_v1
import lib.config as libconfig
import requests
import yaml

import services.datacommons as dc

cfg = libconfig.get_config()

# ----------------------------- INTERNAL FUNCTIONS -----------------------------


class Context:
    """Holds clients to interact with Language client and TF models."""

    def __init__(self):
        self.language_client = language_v1.LanguageServiceClient()
        if not cfg.TEST and cfg.AI_CONFIG_PATH:
            self.inference_client = create_inference_client(cfg.AI_CONFIG_PATH)
        else:
            self.inference_client = None


class InferenceClient(object):
    """Client for interacting with models on the Vertex AI platform."""

    def __init__(
        self,
        region: str,
        endpoint_id: str,
        deployed_model_id: str,
        predict_timeout: int = 30,
    ) -> None:
        self.region = region
        self.endpoint_id = endpoint_id
        self.deployed_model_id = deployed_model_id
        self.predict_timeout = predict_timeout
        self.initialize()

    def initialize(self) -> None:
        pass

    def request(self, query: str):
        pass


class RestInferenceClient(InferenceClient):

    def initialize(self):
        self.creds, self.project_id = None, None
        if not self.deployed_model_id:
            self.creds, self.project_id = google.auth.default()
            self.url = f"https://{self.region}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.region}/endpoints/{self.endpoint_id}:predict"
        else:
            self.url = f"http://{self.endpoint_id}.aiplatform.googleapis.com/v1/models/{self.deployed_model_id}:predict"

        logging.info("RestInferenceClient will use URL: %s", self.url)
        self.session = self._get_session()

    def _get_session(self) -> requests.Session:
        """Gets a http session."""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "datcom-inference-client",
        })
        return session

    def _get_headers(self) -> Optional[Mapping[str, str]]:
        if not self.creds:
            return None
        if not self.creds.valid:
            self.creds.refresh(google.auth.transport.requests.Request())
        return {
            "X-Goog-User-Project": self.project_id,
            "Authorization": "Bearer " + self.creds.token,
        }

    def request(self, query: str):
        headers = self._get_headers()
        json_data = json.dumps({"instances": [query]})
        return self.session.post(self.url,
                                 data=json_data,
                                 headers=headers,
                                 timeout=self.predict_timeout).json()


def get_region() -> Optional[str]:
    """Returns a string indicating the region."""
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/zone"
    metadata_flavor = {"Metadata-Flavor": "Google"}
    zone = requests.get(metadata_url, headers=metadata_flavor).text
    # zone is in the format of projects/projectnum/zones/zone
    region = "-".join(zone.split("/")[3].split("-")[0:2])
    return region


def create_inference_client(config_path: str) -> Optional[InferenceClient]:
    """Creates an InferenceClient instance for generic model predictions."""

    logging.info("Loading InferenceClient using config file %s", config_path)

    factory = {
        "rest": RestInferenceClient,
    }

    with open(config_path) as f:
        ai = yaml.full_load(f)
        if not ai:
            logging.info("No configuration found for ai model")
            return
        # We use a fake region when locally testing with LocalConfig.
        region = ai["local"]["region"] if cfg.LOCAL else get_region()
        logging.info("Searching for model specification for region %s", region)
        if region in ai:
            endpoint_id = ai[region]["endpoint_id"]
            deployed_model_id = ai[region].get("deployed_model_id", "")
            protocol = ai[region]["protocol"]
            cls = factory.get(protocol, None)
            if cls:
                return cls(region, endpoint_id, deployed_model_id)
            raise ValueError(f"Unknown protocol {protocol}")
        else:
            logging.info("No configuration found for region %s", region)


# ----------------------------- SEARCH FUNCTIONS -----------------------------

_MAX_SEARCH_RESULTS = 1000
_RE_KV_ASSIGNMENT = re.compile(r"(\w+)=([^=]*\b(?!=))")
_RE_PLACEHOLDER_NORMALIZE = re.compile(r"<(extra_id_.*?)>")


def _iterate_property_value(
    text: str,
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = ()
) -> Iterator[Tuple[str, str]]:
    """Returns a series of (key, value) tuples from a k = v string."""
    # Normalize spaces around equal sign so that the negative lookahead works
    text = text.replace(" =", "=").replace("= ", "=")
    # We remove <> brackets used for placeholder as they break the other regex.
    text = re.sub(_RE_PLACEHOLDER_NORMALIZE, r"\1", text)
    for match in re.finditer(_RE_KV_ASSIGNMENT, text):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if (include is None or key in include) and key not in exclude:
            yield (key, value)


def _get_places(language_client: language_v1.LanguageServiceClient,
                query: str) -> Sequence[language_v1.Entity]:
    """Returns a list of entities that are of type LOCATION."""
    document = language_v1.Document(content=query,
                                    type_=language_v1.Document.Type.PLAIN_TEXT)
    response = language_client.analyze_entities(request={
        "document": document,
        "encoding_type": language_v1.EncodingType.UTF8
    })
    locations = [
        e for e in response.entities
        if e.type == language_v1.Entity.Type.LOCATION and "mid" in e.metadata
    ]
    return locations


def _delexicalize_query(query: str,
                        places: Sequence[language_v1.Entity]) -> str:
    """Returns a delexicalized version of query where place mentions are replaced by special IDs."""
    place_spans = [m.text for e in places for m in e.mentions]
    place_spans.sort(key=lambda ts: ts.begin_offset)

    prev = 0
    output = []
    query_bytes = query.encode('utf8')
    for index, place_span in enumerate(place_spans):
        if prev > place_span.begin_offset:
            continue
        output.append(query_bytes[prev:place_span.begin_offset].decode('utf8'))
        output.append(f"<extra_id_{index}>")
        prev = place_span.begin_offset + len(place_span.content.encode('utf8'))

    output.append(query_bytes[prev:].decode('utf8'))
    return ''.join(output)


def _build_query(query: str, key_values: Iterator[Tuple[str, str]]) -> str:
    del query  # unused
    search_query = ' '.join([f"{k} {v}" for k, v in key_values])
    logging.info("Using the following query for match API: %s", search_query)
    return search_query


def _parse_model_response(
        model_response, min_score: float = 0.001) -> Sequence[Tuple[str, str]]:
    property_values = set()
    scores = model_response["predictions"][0]["output_1"]
    predictions = model_response["predictions"][0]["output_0"]
    for raw_score, prediction in sorted(zip(scores, predictions)):
        score = math.exp(raw_score)
        if score < min_score:
            continue
        for key, value in _iterate_property_value(prediction,
                                                  exclude=('place', 'topics')):
            # Apparently these are not considered. It looks like this is a default?
            if key == "statType" and value == "measuredValue":
                continue
            property_values.add((key, value))
    return list(sorted(property_values))


def search(context: Context, query: str) -> Sequence[Mapping[str, str]]:
    if not context.inference_client:
        return {"statVars": [], "places": []}
    place_entities = _get_places(context.language_client, query)
    if not place_entities:
        return {"statVars": [], "places": []}
    delexicalized_query = _delexicalize_query(query, place_entities)
    logging.info("Model search on query: %s - %s", query, delexicalized_query)
    model_response = context.inference_client.request(delexicalized_query)
    property_values = _parse_model_response(model_response)
    matches = dc.match_statvar(_build_query(delexicalized_query,
                                            property_values),
                               limit=10,
                               debug=True)
    if "matchInfo" not in matches:
        return {"statVars": [], "places": []}
    statvars = [{
        "name": f"{m['statVarName']} (ID {m['statVar']})",
        "dcid": m["statVar"],
    } for m in matches["matchInfo"]]
    places = [{"name": entity.name} for entity in place_entities]

    debug_lines = [
        f"# query:\n{query}", f"# delexicalized_query:\n{delexicalized_query}",
        f"# model_response:\n{json.dumps(model_response, sort_keys=True, indent=4)}",
        f"# property_value:\n{property_values}", f"# Results:\n"
    ]

    for match in matches["matchInfo"]:
        debug_lines.append(f"# ID: {match['statVar']}")
        debug_lines.append(f"# Statvar: {match['statVarName']}")
        debug_lines.append(f"# Score: {match.get('score', 'n/a')}")
        debug_lines.append(f"# Explanation: {match['explanation']}")

    response = {
        "statVars": statvars,
        "places": places,
        "debug": ['\n'.join(debug_lines)],
    }
    return response
