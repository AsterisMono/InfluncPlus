# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field


class LinkItem(scrapy.Item):
    url = Field()
    title = Field()


class FriendPageLinkItem(LinkItem):
    pass


class BlogLinkItem(LinkItem):
    src_blog = Field()
    pass
