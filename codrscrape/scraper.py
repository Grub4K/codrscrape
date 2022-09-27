import json
import logging
import re
import string
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from codrscrape.utils import convert_md, traverse, try_float

ALLOWED_ID_CHARS = string.ascii_letters + string.digits

logger = logging.getLogger(__name__)


class Scraper:
    _DOWNLOAD_REGEX = re.compile(r"^Direct\s+Download")
    _UPLOADER_REGEX = re.compile(
        r"\|([^\|]*?\s*?)?by:? (?P<uploader>.*)\|?", re.IGNORECASE
    )

    def __init__(self, /):
        self.session = requests.Session()

    def extract_list(self, url, /):
        def match_content_link(tag: Tag):
            return tag.name == "a" and tag.get("target") == "_self"

        def match_next_page_link(tag: Tag):
            return tag.name == "a" and "next" in (tag.get("class") or [])

        next_url = url
        while True:
            logger.info(f"Extracting content list: {next_url}")
            with self.session.get(next_url) as response:
                soup = BeautifulSoup(response.content, "html.parser")

            tags = soup.find_all(match_content_link)
            yield from (tag.get("href") for tag in tags)
            logger.info(f"Reached end of current page")

            next_tag = soup.find(match_next_page_link)
            next_url = next_tag.get("href") if isinstance(next_tag, Tag) else None
            if not isinstance(next_url, str):
                logger.info(f"Reached final page for {url}")
                return

    def extract_single(self, url, /):
        logger.info(f"Extracting content: {url}")
        with self.session.get(url) as response:
            soup = BeautifulSoup(response.content, "html.parser")
        return self.convert_soup(soup, url), self.get_raw(soup)

    def convert_soup(self, soup, url):
        graph_data = traverse(self._get_graph_data(soup), ["@graph"])
        article = traverse(graph_data, [lambda _, data: data.get("@type") == "Article"])

        site_rating, user_rating = self._get_rating(soup)
        thumbnail = traverse(article, ["thumbnailUrl"])
        content_id = self.make_id(url)
        data = {
            "url": url,
            "id": content_id,
            "type": self._make_type(article),
            "title": traverse(article, ["headline"]),
            "uploader": self._get_uploader(soup),
            "description": self._get_description(soup),
            "publish_date": traverse(article, ["datePublished"]),
            "modified_date": traverse(article, ["dateModified"]),
            "thumbnail": thumbnail,
            "site_rating": site_rating,
            "user_rating": user_rating,
            "download": self._get_download(soup),
        }
        is_incomplete = any(value is None for value in data.values())
        if is_incomplete:
            if content_id:
                message = f"{content_id} ({url}): Incomplete entry"
            else:
                message = f"{url}: Incomplete entry"
            logger.warning(message)
        data.update(
            {
                "images": [
                    image for image in self._get_images(soup) if image != thumbnail
                ],
                "videos": self._get_videos(soup),
                "incomplete": is_incomplete,
            }
        )
        return data

    def make_id(self, url):
        path = unquote(urlparse(url).path.strip("/"))
        return "".join(
            char if char in ALLOWED_ID_CHARS else "_" if char == "/" else "-"
            for char in path
        )

    def _make_type(self, article):
        raw_type = traverse(article, ["articleSection", 0])
        if not isinstance(raw_type, str):
            return "unknown"
        return "".join(
            char.lower() if char in ALLOWED_ID_CHARS else "_" for char in raw_type
        )

    def _get_graph_data(self, soup: BeautifulSoup):
        tag = soup.find("script", type="application/ld+json")
        if not isinstance(tag, Tag):
            return None

        return json.loads(tag.text)

    def _get_description(self, soup: BeautifulSoup):
        tag = soup.find("div", {"class": "elementor-text-editor"})
        if not isinstance(tag, Tag):
            return None

        return convert_md(tag)

    def _get_uploader(self, soup: BeautifulSoup):
        tag = soup.find("h2")
        if not isinstance(tag, Tag):
            return None
        uploader_text = "|".join(map(str.strip, map(str, tag.children)))
        if uploader_text is None:
            return None
        uploader = self._UPLOADER_REGEX.search(uploader_text)
        if uploader is None:
            return None
        return uploader.group("uploader")

    def _get_rating(self, soup: BeautifulSoup):
        match_rating_tag = lambda tag: tag.has_attr("data-rating")
        ratings = soup.find_all(match_rating_tag)

        match ratings:
            case [site, user]:
                if site.get("data-rater-readonly") == "false":
                    site, user = user, site
                ratings = (
                    try_float(site.get("data-rating")),
                    try_float(user.get("data-rating")),
                )

            case [tag]:
                rating = try_float(tag.get("data-rating"))
                if tag.get("data-rater-readonly") == "false":
                    return rating, 0.0
                else:
                    return 0.0, rating

        return 0.0, 0.0

    def _get_images(self, soup: BeautifulSoup):
        def match_image_tag(tag):
            return (
                tag.name == "a"
                and tag.has_attr("data-elementor-lightbox-slideshow")
                and tag.findChild("img")
            )

        image_tags = soup.find_all(match_image_tag)
        return [tag.get("href") for tag in image_tags]

    def _get_videos(self, soup: BeautifulSoup):
        video_tags = soup.find_all("div", {"class": "elementor-widget-video"})
        return [
            traverse(
                json.loads(tag.get("data-settings")),
                [lambda name, _: "url" in name],
            )
            for tag in video_tags
        ]

    def _get_download(self, soup: BeautifulSoup):
        def match_download_tag(tag):
            return tag.name == "a" and tag.findChild(text=self._DOWNLOAD_REGEX)

        tag = soup.find(match_download_tag)
        if not isinstance(tag, Tag):
            return None
        return tag.get("href")

    def _get_data_section_count(self, soup: BeautifulSoup):
        tag = soup.find("div", {"class": "elementor-text-editor"})
        if not isinstance(tag, Tag):
            return []

        section_tag = tag.find_parent("section")
        if section_tag is None:
            return []

        return [
            result
            for result in section_tag.find_next_siblings("section")
            if isinstance(result, Tag)
        ]

    def get_raw(self, soup: BeautifulSoup):
        tag = soup.find("div", {"class": "elementor-section-wrap"})
        if not isinstance(tag, Tag):
            return None
        return tag.decode(formatter="html5")
