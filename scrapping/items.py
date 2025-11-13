# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

# Item pour l'atelier
class AtelierItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    category = scrapy.Field()
    price = scrapy.Field()
    location = scrapy.Field()
    duration = scrapy.Field()
