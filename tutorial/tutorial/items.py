# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TutorialItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    price = scrapy.Field()
    category = scrapy.Field()
    location = scrapy.Field()
    duration = scrapy.Field()
