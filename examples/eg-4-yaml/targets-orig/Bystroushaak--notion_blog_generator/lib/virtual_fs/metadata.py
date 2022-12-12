import yaml

from lib.settings import settings


class Metadata:
    def __init__(self):
        self.page_description = ""
        self.image_index = 0
        self.tags = []

        self.unroll = False
        self.unroll_description = False
        self.unroll_subpages = False
        self.unroll_length = settings.number_of_subpages_in_unroll
        self.unroll_categories = False
        self.number_of_subsubpages = 0

        self.date = None
        self.last_mod = None

        self.refs_from_other_pages = set()

    @classmethod
    def from_yaml(cls, yaml_str):
        data = yaml.load(yaml_str, Loader=yaml.FullLoader)
        if data is None:
            data = {}

        metadata = Metadata()

        alt_descr = data.get("Description", metadata.page_description)
        metadata.page_description = data.get("description", alt_descr)

        if isinstance(metadata.page_description, dict):
            key = list(metadata.page_description.keys())[0]
            val = metadata.page_description[key]
            metadata.page_description = key + ": " + val

        alt_index = data.get("image-index", metadata.image_index)
        metadata.image_index = data.get("image_index", alt_index)

        tags = data.get("tags")
        if tags:
            metadata.tags = [tag.strip() for tag in tags.split(",")]

        date = data.get("date")
        if date:
            metadata.date = str(date).replace("/", "-")

        last_mod = data.get("last-mod")
        if last_mod:
            metadata.last_mod = str(last_mod).replace("/", "-")

        metadata.load_property(data, "unroll", "unroll")
        metadata.load_property(data, "unroll_length", "unroll-len")
        metadata.load_property(data, "unroll_length", "unroll-length")
        metadata.load_property(data, "unroll_subpages", "unroll-subpages")
        metadata.load_property(data, "unroll_categories", "unroll-categories")
        metadata.load_property(data, "unroll_description", "unroll-description")

        return metadata

    def load_property(self, data, property_name, name, default=None):
        default_value = getattr(self, property_name) if default is None else default
        setattr(self, property_name, data.get(name, default_value))

    def create_copy(self):
        metadata = Metadata()

        metadata.page_description = self.page_description
        metadata.image_index = self.image_index
        metadata.tags = self.tags

        metadata.unroll = self.unroll
        metadata.unroll_length = self.unroll_length
        metadata.unroll_subpages = self.unroll_subpages
        metadata.unroll_categories = self.unroll_categories
        metadata.unroll_description = self.unroll_description

        metadata.date = self.date
        metadata.last_mod = self.last_mod

        # metadata.refs_from_other_pages = set(self.refs_from_other_pages)

        return metadata
