import json
import os
import random
import re
from ast import Dict
from datetime import datetime
from logging import Formatter, StreamHandler, getLogger
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

import jpholiday
import requests
import setuptools
import yaml
from dotenv import load_dotenv
from googletrans import Translator
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

LANDSCAPE_DATA_SOURCE = os.environ.get("LANDSCAPE_DATA_SOURCE")
WORKDAY_ONLY = setuptools.distutils.util.strtobool(os.environ.get("WORKDAY_ONLY"))
TODAY = datetime.now(ZoneInfo("Asia/Tokyo"))
WEEKDAY = TODAY.weekday()
LOG_LEVEL = os.environ.get("LOG_LEVEL")
VALID_CHARS = re.compile(r"[a-z0-9\-\ ]")
MULTIPLE_HYPHENS = re.compile(r"-{2,}")
CRUNCHBASE_API_KEY = os.environ.get("CRUNCHBASE_API_KEY")
ORIGINAL_HOLIDAYS = [
    e for e in os.environ.get("ORIGINAL_HOLIDAYS", "").split(",") if not e == ""
]

logger = getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = StreamHandler()
handler.setLevel(LOG_LEVEL)
handler.setFormatter(
    Formatter(
        fmt=f"%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(handler)
logger.propagate = False


class OriginalHoliday(jpholiday.OriginalHoliday):
    def _is_holiday(self, date):
        if date in [datetime.strptime(holiday, '%Y-%m-%d').date() for holiday in ORIGINAL_HOLIDAYS]:
            return True
        return False

    def _is_holiday_name(self, date):
        if date.strftime('%Y-%m-%d') in ORIGINAL_HOLIDAYS:
            return '独自休暇'
        else:
            return None


def send_slack_message(title: str, message_blocks: Sequence[Dict]):
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel_id = os.environ.get("SLACK_CHANNEL_ID")

    try:
        client.chat_postMessage(
            channel=channel_id,
            text=title,
            blocks=message_blocks,
        )
    except SlackApiError as e:
        logger.error(e)


def fetch_landscape_data():
    response = requests.get(LANDSCAPE_DATA_SOURCE)
    landscape_data = response.text
    landscape_yaml = yaml.safe_load(landscape_data)
    return landscape_yaml


def fetch_github_description(github_url: str) -> str:
    project_name = github_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{project_name}"
    response = requests.get(api_url)
    landscape_data = response.json()
    description = landscape_data["description"]
    description = description if description is not None else "-"
    return description


def fetch_crunchbase_description(crunchbase_url: str) -> str:
    organization = crunchbase_url.split("/")[-1]
    api_url = f"https://api.crunchbase.com/api/v4/entities/organizations/{organization}?field_ids=short_description"
    response = requests.get(
        api_url,
        headers={"accept": "application/json", "X-cb-user-key": CRUNCHBASE_API_KEY},
    )
    crunchbase_data = response.json()
    description = crunchbase_data["properties"]["short_description"]
    description = description if description is not None else "-"
    return description


class LandscapeItem:
    name: str
    project: Optional[str] = "-"
    category: str
    sub_category: str
    description: Optional[str] = "-"
    translated_description: Optional[str] = "-"
    homepage_url: Optional[str] = "-"
    repo_url: Optional[str] = "-"
    crunchbase: Optional[str] = "-"
    logo: str

    def set(self, field_name, value):
        setattr(self, field_name, value)


def random_pickup_item(landscape_yaml) -> LandscapeItem:
    landscape_item = LandscapeItem()

    categories = landscape_yaml["landscape"]
    category = random.choice(categories)
    landscape_item.category = category["name"]

    subcategories = category["subcategories"]
    subcategory = random.choice(subcategories)
    landscape_item.sub_category = subcategory["name"]

    items = subcategory["items"]
    item = random.choice(items)
    landscape_item.name = item["name"]

    for key in [
        "project",
        "homepage_url",
        "repo_url",
        "crunchbase",
        "logo",
        "description",
    ]:
        try:
            value = item[key] if item[key] is not None else "-"
            landscape_item.set(key, value)
        except (KeyError, AttributeError) as e:
            logger.debug(e)

    if landscape_item.description == "-" and landscape_item.repo_url != "-":
        landscape_item.description = fetch_github_description(landscape_item.repo_url)

    if landscape_item.description == "-" and landscape_item.crunchbase != "-":
        landscape_item.description = fetch_crunchbase_description(
            landscape_item.crunchbase
        )

    if landscape_item.description != "-":
        try:
            translator = Translator()
            translated = translator.translate(landscape_item.description, dest="ja")
            landscape_item.translated_description = translated.text
        except Exception as e:
            logger.error(e)

    logger.debug(vars(landscape_item))

    return landscape_item


def normalize(value: str):
    normalized = value.lower().replace(" ", "-")
    normalized = "".join(c if VALID_CHARS.match(c) else "-" for c in normalized)
    normalized = MULTIPLE_HYPHENS.sub("-", normalized, count=1)
    normalized = normalized.rstrip("-")

    return normalized


def generate_landscape_url(landscape_item: LandscapeItem) -> str:
    category = normalize(landscape_item.category)
    subcategory = normalize(landscape_item.sub_category)
    item_name = normalize(landscape_item.name)

    request_param = "--".join([category, subcategory, item_name])
    url = f"https://landscape.cncf.io/?item={request_param}"

    return url


def build_message(landscape_item: LandscapeItem) -> Sequence[Dict]:

    greeting = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "こんにちは皆さん！\n今日も CNCF の Landscape の中から素晴らしいプロダクトやメンバーを紹介します ✨",
        },
    }

    icon_image = {
        "type": "image",
        "image_url": f"https://one-cloud-native-a-day-icons.s3.ap-northeast-1.amazonaws.com/{landscape_item.logo}.png",
        "alt_text": landscape_item.name,
    }

    header = {
        "type": "header",
        "text": {"type": "plain_text", "text": landscape_item.name},
    }

    details = {
        "type": "section",
        "fields": [
            {"type": "plain_text", "text": "CNCF PROJECT"},
            {"type": "plain_text", "text": landscape_item.project},
            {"type": "plain_text", "text": "CATEGORY"},
            {"type": "plain_text", "text": landscape_item.category},
            {"type": "plain_text", "text": "SUBCATEGORY"},
            {"type": "plain_text", "text": landscape_item.sub_category},
            {"type": "plain_text", "text": "DESCRIPTION"},
            {"type": "plain_text", "text": landscape_item.description},
            {"type": "plain_text", "text": "DESCRIPTION（自動翻訳）"},
            {"type": "plain_text", "text": landscape_item.translated_description},
        ],
    }

    divider = {"type": "divider"}

    links_header = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": ":link: 各種リンク"},
    }

    links = {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_section",
                "elements": [
                    {"type": "emoji", "name": "sunrise_over_mountains"},
                    {"type": "text", "text": " "},
                    {
                        "type": "link",
                        "url": generate_landscape_url(landscape_item),
                        "style": {"bold": True},
                    },
                ],
            },
            {
                "type": "rich_text_section",
                "elements": [
                    {"type": "emoji", "name": "globe_with_meridians"},
                    {"type": "text", "text": " "},
                    {
                        "type": "link",
                        "url": landscape_item.homepage_url,
                        "style": {"bold": True},
                    },
                ],
            },
            {
                "type": "rich_text_section",
                "elements": [
                    {"type": "emoji", "name": "github"},
                    {"type": "text", "text": " "},
                    {
                        "type": "link",
                        "url": landscape_item.repo_url,
                        "style": {"bold": True},
                    },
                ],
            },
        ],
    }

    blocks = [greeting, icon_image, header, details, divider, links_header, links]

    logger.debug(blocks)

    return blocks


def main():

    if WORKDAY_ONLY and jpholiday.is_holiday(TODAY):
        raise Exception(f"{TODAY} {jpholiday.is_holiday_name(TODAY)}")

    if WORKDAY_ONLY and (WEEKDAY == 5 or WEEKDAY == 6):
        raise Exception(f"{TODAY} 土日")

    landscape_yaml = fetch_landscape_data()

    while (item := random_pickup_item(landscape_yaml)).project == "archived":
        logger.debug("archived プロジェクトを Skip")

    message = build_message(item)
    send_slack_message(":alarm_clock: クラウドネイティブのお時間です！", message)


def lambda_handler(event, context):
    try:
        main()
    except Exception as e:
        logger.info(e)
        return json.dumps({"message": str(e)})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.info(e)
