import random
import requests
from requests.models import Response
from lxml import html
from lxml.etree import _Element, tostring
from typing import Optional, List, Any
from nthscraper.wrapper.requests_wrapper import RequestsWrapper
from nthscraper.wrapper.local_file_adapter import LocalFileAdapter
from nthscraper.by import By, selector_mode_values
from nthscraper.logger import setup_logger

logger = setup_logger()


class NthScraperElement:
    """Represents an HTML element in the nthscraper context."""

    def __init__(self, element: _Element):
        if not isinstance(element, _Element):
            raise ValueError("Expected an lxml.etree._Element instance.")
        self.element: _Element = element

    def find_elements(
        self, by_mode: "By", to_search: str, tag: str = "node()"
    ) -> List["NthScraperElement"]:
        """Find multiple elemnts within this element."""
        err_message, xpath = selector_mode_values(by_mode, to_search, tag)
        try:
            elements = self.element.xpath(xpath)
            return (
                [NthScraperElement(element) for element in elements] if elements else []
            )
        except Exception:
            logger.error(f"{err_message}: {e}")
            return []

    def find_element(self, by_mode: "By", to_search: str) -> "NthScraperElement":
        """
        Attempt to find an HTML element by XPATH or other methods and return it wrapped in a NthScraperElement
        """
        _, xpath = selector_mode_values(by_mode, to_search)
        try:
            element = self.element.xpath(xpath)[0]
        except Exception:
            raise ValueError("Failed to find element.")
        return NthScraperElement(element)

    def get_text(self, all_text_content: bool = True) -> str:
        """
        all_text_content: if True (default), return all the text content of the element
        else return text content of the element (sub element excluded)
        """
        if all_text_content is True:
            return "".join(self.element.itertext())
        return self.element.text if self.element.text is not None else ""

    def get_tag_name(self) -> str:
        """Get the tag name of the element."""
        return self.element.tag

    def get_attribute(
        self, attribute: str, inner_text_filter: List[str] = ["\n", "\t"]
    ) -> str:
        """
        Retrieve various attributes or data from an HTML element including innerText and innerHtml
        :param attribute: Name of the attribute (e.g., 'class', 'id', 'innerText', 'innerHTML')
        :param inner_text_filter: Filters to apply for filtering innerText,
        :return: attributes as string
        """
        if attribute == "innerText":
            text = self.get_text()
            for rep in inner_text_filter:
                text = text.replace(rep, "")
            return text.strip()
        if attribute == "innerHTML":
            return tostring(self.element, encoding="unicode", method="html")

        attr_value = self.element.get(attribute)
        if attr_value is None:
            raise ValueError(f"Error accessing the attribute {attribute}")

        return attr_value

    def get_parent(self) -> Optional["NthScraperElement"]:
        parent = self.element.getparent()
        return NthScraperElement(parent) if parent is not None else None

    def get_children(self, tag_name: str = "*") -> List["NthScraperElement"]:
        """Get children of elements filtered by tag name"""
        children = self.element.findall(tag_name)
        return [NthScraperElement(child) for child in children]

    def __str__(self):
        """Representation of NthScraperElement object."""
        return f"NthScraperElement: <{self.get_tag_name()}> element instance."


class NthScraper:
    """class to scrape websites following selenium-like rules"""

    def __init__(self) -> None:
        self.requests_wrapper: RequestsWrapper = RequestsWrapper()
        self.doc = None
        self.response: Optional[Response] = None

    def _get_response(
        self,
        url: str,
        sleep_seconds: Optional[int] = None,
        is_post: bool = False,
        **kwargs: Any,
    ):
        sleep_seconds = (
            sleep_seconds if sleep_seconds is not None else random.randint(1, 5)
        )
        method = self.requests_wrapper.post if is_post else self.requests_wrapper.get
        self.response = method(url, sleep_seconds=sleep_seconds, **kwargs)
        self.doc = (
            html.fromstring(self.response.content) if self.response.content else None
        )
        return self.response

    def get(self, url: str, sleep_seconds: Optional[int] = None, **kwargs: Any):
        return self._get_response(url, sleep_seconds, **kwargs)

    def get_from_local(self, file_path: str) -> Response:
        session = requests.session()
        session.mount("file://", LocalFileAdapter())
        self.response = session.get(f"file://{file_path}")
        logger.info(f"Scraping data from: {file_path}")
        self.doc = (
            html.fromstring(self.response.content) if self.response.content else None
        )
        self.response.close()
        return self.response

    def post(self, url: str, sleep_seconds: Optional[int] = None, **kwargs: Any):
        return self._get_response(url, sleep_seconds, is_post=True, **kwargs)

    def find_elements(
        self,
        by_mode: "By",
        to_search: str,
        doc: Optional[html.HtmlElement] = None,
        tag: str = "node()",
    ) -> List["NthScraperElement"]:
        err_message, xpath = selector_mode_values(by_mode, to_search, tag)
        doc = doc if doc else self.doc

        if doc is None or len(doc) == 0:
            logger.error("Document is not loaded properly for xpath operations.")
            return []
        try:
            elements = doc.xpath(xpath)
            return (
                [NthScraperElement(element) for element in elements] if elements else []
            )
        except Exception as e:
            logger.error(f"{err_message}: {e}")
            return []

    def find_element(
        self,
        by_mode: "By",
        to_search: str,
        doc: Optional[html.HtmlElement] = None,
        tag: str = "node()",
    ) -> "NthScraperElement":
        err_message, xpath = selector_mode_values(by_mode, to_search, tag)
        doc = doc if doc else self.doc
        if doc is None or len(doc) == 0:
            raise ReferenceError("HTML Document is not a valid lxml object")
        try:
            element = doc.xpath(xpath)[0]
            return NthScraperElement(element)
        except Exception:
            raise ValueError("Failed to find Element")

        return NthScraperElement(element)
