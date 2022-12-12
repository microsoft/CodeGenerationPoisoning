"""
functions to generate the in-built
widgets ready to send to the user
"""
from flask import render_template

from ..database import dao


def generate_widget_container(widget_id: int, widget_html: str) -> str:
    """
    returns the generated widget container

        :param widget_id: the widget id
        :param widget_html: the widget html
        :return: the rendered html
    """
    return f"<div id='widget-{widget_id}'>{widget_html}</div>"


def generate_widget_failed(widget_id: int):
    return f"<div class='container' id='widget-{widget_id}'>\
    <p>Widget failed to load, so will be deleted</p></div>"


def generate_shortcut_widget(widget_id: int, widget_settings=None) -> str:
    """
    returns HTML of the widget,
    ready to send to the user

        :param widget_id: the personal widget id
        :param widget_settings: the widget settings
        :return: the str html that has been rendered
    """
    if not widget_settings:
        widget_settings = []
    shortcuts = dao.dashboard.get_shortcuts_by_ids(*widget_settings)
    shortcuts_dict = {}
    for row in shortcuts:
        shortcuts_dict[row.id_] = row
    shortcuts_ordered = (shortcuts_dict[int(i)] for i in widget_settings)
    return render_template("/widgets/shortcuts.html", shortcuts=shortcuts_ordered)


def generate_message_widget(widget_id: int, widget_settings=None) -> str:
    """
    returns HTML of the messages widget,
    ready to send to the user

        :param widget_id: the personal widget id
        :param widget_settings: the widget settings
        :return: the str html that has been rendered
    """
    return render_template("/widgets/messages.html")


def generate_weather_widget(widget_id: int, widget_settings=None) -> str:
    """
    returns HTML of the weather widget,
    ready to send to the user

        :param widget_id: the personal widget id
        :param widget_settings: the widget settings
        :return: the str html that has been rendered
    """
    return render_template("/widgets/weather.html")


def generate_expiring_freezer_manager_widget(widget_id: int, widget_settings=None) -> str:
    items = dao.freezer_manager.get_fm4_expiring()
    return render_template("/widgets/expiring_freezer_manager.html", items=items)
