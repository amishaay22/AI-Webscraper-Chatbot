# import scrapy
# from itemloaders import ItemLoader
# from ..items import ScrapingItem
# from scrapy.linkextractors import LinkExtractor
# from urllib.parse import urlparse


# class URLScraper(scrapy.Spider):

#     name = "url_scraper"

#     def __init__(self, urls=None, **kwargs):

#         super().__init__(**kwargs)

#         if isinstance(urls, str):
#             self.start_urls = [u.strip() for u in urls.split(",")]
#         else:
#             self.start_urls = urls or []

#         # Allow redirects
#         self.allowed_domains = []

#     def start_requests(self):

#         for url in self.start_urls:

#             yield scrapy.Request(
#                 url=url,
#                 callback=self.parse
#             )

#     def parse(self, response):

#         loader = ItemLoader(
#             item=ScrapingItem(),
#             response=response
#         )

#         # URL
#         loader.add_value(
#             "url",
#             response.url
#         )

#         # TITLE
#         title = response.css(
#             "title::text"
#         ).get()

#         loader.add_value(
#             "title",
#             title
#         )

#         # MAIN CONTENT ONLY
#         content = response.xpath(
#             """
#             //main//text()[
#                 not(parent::script)
#                 and not(parent::style)
#                 and normalize-space()
#             ]
#             """
#         ).getall()

#         # FALLBACK IF <main> TAG NOT FOUND
#         if not content:

#             content = response.xpath(
#                 """
#                 //body//text()[
#                     not(parent::script)
#                     and not(parent::style)
#                     and normalize-space()
#                 ]
#                 """
#             ).getall()

#         # CLEAN CONTENT
#         cleaned_content = " ".join(
#             text.strip()
#             for text in content
#             if text.strip()
#         )

#         print("CONTENT LENGTH:", len(cleaned_content))

#         loader.add_value(
#             "content",
#             cleaned_content
#         )

#         yield loader.load_item()

#         # FOLLOW ONLY INTERNAL LINKS
#         le = LinkExtractor()

#         current_domain = urlparse(
#             response.url
#         ).netloc

#         for link in le.extract_links(response):

#             link_domain = urlparse(
#                 link.url
#             ).netloc

#             if link_domain == current_domain:

#                 yield response.follow(
#                     link.url,
#                     callback=self.parse
#                 )


import scrapy
import re
from itemloaders import ItemLoader
from ..items import ScrapingItem
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse


class URLScraper(scrapy.Spider):

    name = "url_scraper"

    # Safety limits
    custom_settings = {
        "DEPTH_LIMIT": 2,
        "CLOSESPIDER_PAGECOUNT": 50,
    }

    def __init__(self, urls=None, **kwargs):

        super().__init__(**kwargs)

        if isinstance(urls, str):
            self.start_urls = [
                u.strip()
                for u in urls.split(",")
            ]
        else:
            self.start_urls = urls or []

        self.allowed_domains = []

    # -----------------------------------
    # FIX BROKEN CHARACTER SPACING
    # -----------------------------------
    def fix_broken_spacing(self, text):

        words = text.split()

        if not words:
            return text

        # ratio of single-char words
        single_char_ratio = (
            sum(1 for w in words if len(w) == 1)
            / len(words)
        )

        # only fix when text is heavily broken
        if single_char_ratio > 0.6:

            text = "".join(words)

            # restore sentence spacing
            text = re.sub(
                r"([.!?])([A-Z])",
                r"\1 \2",
                text
            )

        return text

    # -----------------------------------
    # START REQUESTS
    # -----------------------------------
    def start_requests(self):

        for url in self.start_urls:

            yield scrapy.Request(
                url=url,
                callback=self.parse
            )

    # -----------------------------------
    # MAIN PARSER
    # -----------------------------------
    def parse(self, response):

        loader = ItemLoader(
            item=ScrapingItem(),
            response=response
        )

        # -----------------------------------
        # URL
        # -----------------------------------
        loader.add_value(
            "url",
            response.url
        )

        # -----------------------------------
        # TITLE
        # -----------------------------------
        title = response.css(
            "title::text"
        ).get()

        if title:
            loader.add_value(
                "title",
                title.strip()
            )

        # -----------------------------------
        # CONTENT EXTRACTION
        # -----------------------------------
        content_nodes = response.xpath("""
            //article//h1 |
            //article//h2 |
            //article//h3 |
            //article//p |
            //article//li |

            //main//h1 |
            //main//h2 |
            //main//h3 |
            //main//p |
            //main//li |

            //body//h1 |
            //body//h2 |
            //body//h3 |
            //body//p |
            //body//li
        """).getall()

        cleaned = []
        seen = set()

        for node in content_nodes:

            text = scrapy.Selector(
                text=node
            ).xpath("string(.)").get()

            if not text:
                continue

            text = text.strip()

            # Fix broken spacing
            text = self.fix_broken_spacing(text)

            # normalize whitespace
            text = re.sub(
                r"\s+",
                " ",
                text
            ).strip()

            # skip tiny/noisy text
            if len(text) < 20:
                continue

            # remove duplicates
            normalized = text.lower()

            if normalized not in seen:
                seen.add(normalized)
                cleaned.append(text)

        cleaned_content = "\n".join(cleaned)

        print("SCRAPED:", response.url)
        print("CONTENT LENGTH:", len(cleaned_content))

        loader.add_value(
            "content",
            cleaned_content
        )

        yield loader.load_item()

        # -----------------------------------
        # FOLLOW INTERNAL LINKS + SUBDOMAINS
        # -----------------------------------
        le = LinkExtractor()

        current_domain = urlparse(
            response.url
        ).netloc

        for link in le.extract_links(response):

            link_domain = urlparse(
                link.url
            ).netloc

            # allow:
            # toscrape.com
            # books.toscrape.com
            # quotes.toscrape.com
            if (
                link_domain == current_domain
                or link_domain.endswith("." + current_domain)
                or current_domain.endswith("." + link_domain)
            ):

                yield response.follow(
                    link.url,
                    callback=self.parse
                )