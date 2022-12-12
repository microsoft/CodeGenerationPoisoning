"""The site module contains definitions of models like User and Application.

The models defined in this module can for example be used for

- Galleries
- Menus
- Governance. I.e. restricting access to certain applications for specific users.
- And much more.
"""
import uuid
from typing import List

import markdown
import panel as pn
import param
import yaml

from awesome_panel_extensions.assets.svg_icons import ICONS

AVATAR_URL = (
    "https://raw.githubusercontent.com/MarcSkovMadsen/awesome-panel-assets/master/awesome-panel/"
    "avatar.png"
)
MARKDOWN_EXTENSIONS = ["extra", "smarty", "codehilite"]
STYLE = """
img.pnx-avatar {
    height:100%;
    width:100%;
    border-radius:50%;
    vertical-align: middle;
}
.pnx-resource img.pnx-avatar {
    height: 2em;
    width: 2em;
    margin-left: 0.5em;
}
.pnx-resource svg.pnx-icon {
    height: 1.5em;
    margin-left: 0.5em;
    vertical-align: middle;
    fill: currentColor;
}
.pnx-resource svg.pnx-icon.pnx-icon-binder {
    width: 5em;
}
.pnx-resource a {
    text-decoration: none;
}
"""

def _add_css():
    if not STYLE in pn.config.raw_css:
        pn.config.raw_css.append(STYLE)

def _get_nested_value(element, *keys):
    """Returns a nested value if it exists. Otherwise None

    If 'panel' is a key of element then we search from the value of 'panel'"""
    if not isinstance(element, dict):
        raise AttributeError("Expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError("Expects at least two arguments, one given.")

    if "panel" in element:
        element = element["panel"]

    if "config" in element:
        element = element["config"]

    for key in keys:
        try:
            element = element[key]
        except KeyError:
            return None
    return element


def _skip(item):
    """Returns True if the item is a dictionary with the key 'skip' and value True"""
    if not isinstance(item, dict):
        return False
    return item.get("skip", False)


class _BaseModel(param.Parameterized):
    """The BaseModel adds ordering by the name parameter to a Class"""

    uid = param.String(constant=True, doc="A unique id identifying the item.", precedence=1)
    name = param.String(default="New Model", doc="The name of the item", precedence=1)
    category = param.String(default="Other", doc="A category name", precedence=1)
    tags = param.List(
        class_=str,
        precedence=3,
        doc="""A list of tags like 'machine-learning', 'panel', 'holoviews'.""",
    )
    resources = param.Dict(
        precedence=3,
        doc="""
        A dictionary of urls. For example 'github': 'https://panel.holoviz.org'""",
    )

    def __init__(self, **params):
        if "uid" not in params:
            params["uid"] = str(uuid.uuid4())
        if "resources" not in params:
            params["resources"] = {}

        super().__init__(**params)

    def __lt__(self, other):
        if hasattr(other, "name"):
            return self.name.casefold() < other.name.casefold()
        return True

    def __eq__(self, other):
        if hasattr(other, "uid"):
            return self.uid == other.uid
        return False

    def __str__(
        self,
    ):
        return self.name

    def __repr__(
        self,
    ):
        return f"{self.__class__.name}(name='{self.name}')"


class User(_BaseModel):
    """A Model of a User

    >>> from awesome_panel_extensions.site.models import User
    >>> User(
    ...     name = "Philipp Rudiger",
    ...     url = "https://github.com/philippjfr",
    ...     email = "na@hotmail.com",
    ...     avatar = "https://avatars.githubusercontent.com/u/1550771",
    ...     tags = ["pyviz", "developer"],
    ...     resources = {"twitter": "https://twitter.com/PhilippJFR"},
    ... )
    User(name='Philipp Rudiger')
    """

    name = param.String(default="New User", doc="The name of the user.", precedence=1)

    email = param.String(doc="The email of the user.", precedence=1)
    url = param.String(doc="An url pointing to a page about the user.", precedence=1)

    avatar = param.String(
        default=AVATAR_URL, doc="The url of an avatar image of the user.", precedence=2
    )

    @staticmethod
    def _get_users(config):
        """Returns a list of Users from the specificed list of dicts"""
        if not config:
            return []

        users = _get_nested_value(config, "users")
        if not users:
            return []
        users = [{key: value for key, value in user.items() if value} for user in users]
        return [User(**user) for user in users if not _skip(user)]

    def _repr_html_(self):
        # pylint: disable=line-too-long
        return f"""<a href="{ self.url }" target="_blank"><img src="{ self.avatar }" class="pnx-avatar" alt="Avatar" title="{ self.name }"></a>"""


class Application(_BaseModel):
    """A Model of an Application

    >>> from awesome_panel_extensions.site.models import User, Application
    >>> philipp = User(
    ...     name = "Philipp Rudiger",
    ...     url = "https://github.com/philippjfr",
    ...     email = "na@hotmail.com",
    ...     avatar = "https://avatars.githubusercontent.com/u/1550771",
    ...     resources = {"twitter": "https://twitter.com/PhilippJFR"},
    ...     tags = ["pyviz", "developer"],
    ... )
    >>> Application(
    ...     name = "Panel",
    ...     description = "The analytics app framework to rule them all",
    ...     description_long = "Turns every dash into something lit",
    ...     author = philipp,
    ...     owner = philipp,
    ...     url = "https://panel.holoviz.org",
    ...     thumbnail = "https://panel.holoviz.org/_static/logo_stacked.png",
    ...     resources = {"github": "https://github.com/holoviz/panel"},
    ...     tags = ["awesome", "analytics", "apps"]
    ... )
    Application(name='Panel')
    """

    name = param.String(
        default="New Application",
        precedence=1,
        doc="""
        The name of the application""",
    )

    author = param.ClassSelector(class_=User, constant=True, precedence=1)
    owner = param.ClassSelector(class_=User, constant=True, precedence=1)

    description = param.String(
        regex="^.{0,150}$",
        precedence=1,
        doc="""
        A short text introduction of max 150 characters.""",
    )
    description_long = param.String(
        precedence=1,
        doc="""
        A longer description. Can contain Markdown and HTML""",
    )
    project = param.String(
        doc="""
    The name of associated project. Can be used for governance in a multi-project site""",
        precedence=1,
    )
    servable = param.String(precedence=2, doc="The path to a servable Panel application")
    url = param.String(precedence=2, doc="The url of the application.")
    thumbnail = param.String(precedence=2, doc="The url of a thumbnail of the application.")

    def __init__(self, **params):
        for key in ["author", "owner"]:
            if key in params:
                user = params[key]
                if isinstance(user, str):
                    params[key] = User(uid=user, name=user)
            else:
                params[key] = User()

        super().__init__(**params)

    @staticmethod
    def _get_applications(config, users):
        """Returns a list of Applications from the specificed list of dicts.

        users is a list of existing Users
        """
        if not config:
            return []

        user_map = {user.uid: user for user in users}

        applications = _get_nested_value(config, "applications")
        if not applications:
            return []

        for application in applications:
            for key in ["author", "owner"]:
                if key in application:
                    user = application[key]
                    if user in user_map:
                        application[key] = user_map[user]
        applications = [
            {key: value for key, value in application.items() if value}
            for application in applications
        ]
        return [
            Application(**application) for application in applications if not _skip(application)
        ]

    @classmethod
    def read(cls, file) -> List["Application"]:
        """Returns a list of Applications from the specified file

        Currently only yaml is supported

        Args:
            path (str|pathlib.Path): The path to the file
        Returns:
            List[Application]: A list of applications
        """
        with open(file, "r") as stream:
            config = yaml.safe_load(stream)
        users = User._get_users(config)  # pylint: disable=protected-access
        return cls._get_applications(config, users)

    @staticmethod
    def _get_url_icon_html(
        title,
        url,
    ):
        return (
            f"""<a title="{ title }" appearance="hypertext" href="{ url }" target="_blank">"""
            f"""{ ICONS[title] }</a>"""
        )

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        return markdown.markdown(text, extensions=MARKDOWN_EXTENSIONS, output_format="html5")

    def intro_section(self) -> pn.pane.HTML:
        """An panel with a text introduction to the Resource

        Returns:
            pn.pane.HTML: The Intro Section panel.
        """
        _add_css()
        
        return pn.pane.HTML(self._repr_html_())

    def _repr_html_(self):
        description = self._markdown_to_html(self.description_long)
        html = f"""<div class="pnx-resource">
        <h1 class="pnx-header">{ self.name }</h1>
        <p>{ description }</p>
        """
        if self.author:
            # pylint: disable=protected-access
            html += f"""<p><strong>Authors:</strong>{ self.author._repr_html_() }</p>"""

        code_url = self.resources.get("code", "")
        if code_url:
            code = self._get_url_icon_html("code", code_url)
            html += "<p><strong>Code:</strong>" + code + "</p>"
        resources = ""
        for item in ["doc", "gif", "mp4", "youtube", "binder"]:
            url = self.resources.get(item, "")
            if url:
                resources += self._get_url_icon_html(item, url)

        if resources:
            html += "<p><strong>Resources:</strong>" + resources + "</p>"

        tags = ", #".join(self.tags)
        if tags:
            html += "<p><strong>Tags:</strong> #" + tags.lower() + "</p>"

        html += "</div>"
        return html
