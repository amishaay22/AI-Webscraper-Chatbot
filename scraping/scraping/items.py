import scrapy
from itemloaders.processors import TakeFirst, MapCompose


class ScrapingItem(scrapy.Item):

    url = scrapy.Field(output_processor=TakeFirst())

    title = scrapy.Field(output_processor=TakeFirst())

    content = scrapy.Field(
        input_processor=MapCompose(str.strip),
        output_processor=TakeFirst()
    )