from textwrap import dedent

import yaml

from jetstream import argo
from jetstream.cli import ArgoExecutorStrategy


class TestArgo:
    def test_apply_parameters(self):
        config_str = dedent(
            """
            apiVersion: argoproj.io/v1alpha1
            kind: Workflow
            metadata:
                generateName: jetstream-
            spec:
                entrypoint: jetstream
                arguments:
                    parameters:
                    - name: date
            """
        )

        manifest = yaml.safe_load(config_str)
        updated_manifest = argo.apply_parameters(manifest, {"date": "2020-01-01"})
        assert updated_manifest["spec"]["arguments"]["parameters"][0]["name"] == "date"
        assert updated_manifest["spec"]["arguments"]["parameters"][0]["value"] == "2020-01-01"

    def test_apply_parameters_overwrite(self):
        config_str = dedent(
            """
            apiVersion: argoproj.io/v1alpha1
            kind: Workflow
            metadata:
                generateName: jetstream-
            spec:
                entrypoint: jetstream
                arguments:
                    parameters:
                    - name: date
                      value: 2020-12-12
            """
        )

        manifest = yaml.safe_load(config_str)
        updated_manifest = argo.apply_parameters(manifest, {"date": "2020-01-01"})
        assert updated_manifest["spec"]["arguments"]["parameters"][0]["name"] == "date"
        assert updated_manifest["spec"]["arguments"]["parameters"][0]["value"] == "2020-01-01"

    def test_apply_parameters_add(self):
        config_str = dedent(
            """
            apiVersion: argoproj.io/v1alpha1
            kind: Workflow
            metadata:
                generateName: jetstream-
            spec:
                entrypoint: jetstream
                arguments:
                    parameters:
                    - name: date
                      value: 2020-12-12
            """
        )

        manifest = yaml.safe_load(config_str)
        updated_manifest = argo.apply_parameters(manifest, {"date": "2020-01-01", "slug": "test"})
        assert updated_manifest["spec"]["arguments"]["parameters"][0]["name"] == "date"
        assert updated_manifest["spec"]["arguments"]["parameters"][0]["value"] == "2020-01-01"
        assert updated_manifest["spec"]["arguments"]["parameters"][1]["name"] == "slug"
        assert updated_manifest["spec"]["arguments"]["parameters"][1]["value"] == "test"

    def test_experiment_injection(self):
        with open(ArgoExecutorStrategy.RUN_WORKFLOW) as workflow_file:
            manifest = yaml.safe_load(workflow_file)
            updated_manifest = argo.apply_parameters(
                manifest,
                {
                    "experiments": [
                        {"date": "2020-01-01", "slug": "a"},
                        {"date": "2020-01-02", "slug": "b"},
                    ]
                },
            )

            assert updated_manifest["spec"]["arguments"]["parameters"][0]["name"] == "experiments"
            assert (
                updated_manifest["spec"]["arguments"]["parameters"][0]["value"]
                == '[{"date": "2020-01-01", "slug": "a"}, {"date": "2020-01-02", "slug": "b"}]'
            )
