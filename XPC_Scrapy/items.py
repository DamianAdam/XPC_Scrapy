# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class XpcBaseInfoItem(scrapy.Item):
    article_id = scrapy.Field()
    title = scrapy.Field()
    like = scrapy.Field()
    collection = scrapy.Field()


class XpcCommentItem(scrapy.Item):
    comment_id = scrapy.Field()
    timestamp = scrapy.Field()
    content = scrapy.Field()
    article_id = scrapy.Field()


class XpcVideoUrlItem(scrapy.Item):
    article_id = scrapy.Field()
    quality = scrapy.Field()
    url = scrapy.Field()
