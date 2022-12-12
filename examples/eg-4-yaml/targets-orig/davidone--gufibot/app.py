"""
Application Entry point
"""
import os
import re
import sys
import yaml

import slack
from gufi import SlackGufi
from logging_config import LOGGER

RGX_MSG = r"^([a-zA-Z0-9]+)$"


@slack.RTMClient.run_on(event="message")
def rtm_message(**payload):
    """
    Main RTM function to process requests
    """
    data = payload["data"]
    if "subtype" in data and data["subtype"] == "bot_message":
        # We don't reply to bots, only humans
        return
    text = data.get("text", [])
    re_text = re.match(RGX_MSG, text)
    if re_text is None or len(re_text.groups()) == 0:
        return

    if isinstance(text, str) and text.lower() == "fortune":
        fortune_path = "/usr/local/bin/fortune"
        if not (os.path.isfile(fortune_path) or os.access(fortune_path, os.X_OK)):
            fortune_out = f"{fortune_path} not available"
        else:
            fortune_out = os.popen(fortune_path).read()
        channel_id = data["channel"]
        web_client = payload["web_client"]
        web_client.chat_postMessage(channel=channel_id, text=f"```{fortune_out}```")


if __name__ == "__main__":
    try:
        with open("config.yaml", "r") as stream:
            CFG_YAML = yaml.safe_load(stream)
    except FileNotFoundError as exc:
        print(f"{exc}")
        sys.exit(exc.errno)
    SLACK_GUFI = SlackGufi(CFG_YAML)
    SLACK_GUFI.send_message("yo!")
    LOGGER.info("Application started")
    SLACK_GUFI.start()
