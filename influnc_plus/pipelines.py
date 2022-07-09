# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from datetime import datetime

import scrapy.crawler
from itemadapter import ItemAdapter
from scrapy import Request
from scrapy.exceptions import DropItem

from influnc_plus.db.models import Blog, Link


class FilterPipeline:
    keyword_blacklist = []

    def process_item(self, item, spider):
        for keyword in self.keyword_blacklist:
            if keyword in item["title"]:
                raise DropItem("Keyword found in item title, dropping...")


class StripBlankPipeline:
    def process_item(self, item, spider):
        # item.url: UrlParseResult, item.title: str, item.src_blog: Blog
        item["title"] = item["title"].strip().replace("\n", "")
        return item


class SaveToDatabasePipeline:
    def __init__(self, crawler):
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_item(self, item, spider):
        # Blog: domain, title, status
        blog, created = Blog.get_or_create(domain=item["url"].netloc)
        if created:
            blog.title = item["title"]
            blog.status = "unknown"
            blog.last_access_time = datetime.now()
            blog.save()
        link = Link.get_or_create(src_blog=item["src_blog"], dst_blog=blog)
        # crawler: scrapy.crawler.Crawler = self.crawler
        # crawler.engine.crawl(Request(
        #     url="https://" + item["url"].netloc,
        #     callback=spider.parse_blog,
        #     errback=spider.error_handling, cb_kwargs={'src': blog}
        # ), spider)
        return item
