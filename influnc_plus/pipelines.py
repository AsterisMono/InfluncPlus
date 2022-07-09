# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from datetime import datetime

from scrapy.exceptions import DropItem

from influnc_plus.db.models import Blog, Link
from influnc_plus.filter.keyword_tester import Tester
from influnc_plus.util.utils import str_collapse


class StripBlankPipeline:
    def process_item(self, item, spider):
        # item.url: UrlParseResult, item.title: str, item.src_blog: Blog
        item["title"] = str_collapse(item["title"])
        return item


class FilterPipeline:
    def __init__(self):
        self.tester = Tester()

    def process_item(self, item, spider):
        if_updated = self.tester.update()
        if if_updated:
            spider.console_logger.info("[过滤器] 过滤器黑名单已经改变，正在更新...")
        flag, keyword = self.tester.test(item["title"])
        if flag:
            spider.console_logger.info("[{}] 发现关键词: ----> [{}] <----, 条目已丢弃".format(item["title"], keyword))
            raise DropItem("[{}] 发现关键词:{}, 条目已丢弃".format(item["title"], keyword))
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
