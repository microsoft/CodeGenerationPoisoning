import click
import yaml

from cdn_generator.common_files import generate_common_files
from cdn_generator.helpers import set_bucket_id
from cdn_generator.latest_yaml import (
    generate_latest_yaml,
    write_latest_yaml,
)
from cdn_generator.manifest_yaml import generate_manifests
from cdn_generator.directory_listing import (
    generate_directory_listing,
    generate_directory_listing_root,
)


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--bucket-id", help="Id of the S3 Bucket", required=True)
@click.option("--new-release", help="Folder of the new release")
def main(bucket_id, new_release):
    set_bucket_id(bucket_id)

    with open("config.yaml", "r") as f:
        config_yaml = yaml.safe_load(f.read())
    config = {folder["name"]: folder for folder in config_yaml["folders"]}

    if new_release and not new_release.endswith("/"):
        new_release += "/"

    generate_common_files()

    all_versions = []
    for category, category_config in config.items():
        skip_write = new_release and not new_release.startswith(f"{category}/")

        # Always calculate the latest versions for every category. This
        # because there will be a root "latest.yaml", which has to contain
        # the information of all releases. But only write "latest.yaml" for
        # folders in the tree of "new_release".
        category_versions = generate_latest_yaml(category, config=category_config, filter_path=new_release)
        for item in category_versions:
            if "folder" in item:
                item["folder"] = f"{category}/{item['folder']}"
            else:
                item["folder"] = category
        all_versions.extend(category_versions)

        if not skip_write:
            generate_manifests(category, category_config, filter_path=new_release)
            generate_directory_listing(category, config=category_config, filter_path=new_release)

    write_latest_yaml("", all_versions)
    generate_directory_listing_root("", ignore_folders=["static", "errors"])


if __name__ == "__main__":
    main(auto_envvar_prefix="CDN")
