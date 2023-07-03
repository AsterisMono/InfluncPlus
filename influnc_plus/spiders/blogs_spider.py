import logging
from time import sleep
from typing import Tuple
from bs4 import BeautifulSoup as soup
from datetime import datetime
from urllib.parse import urlparse

import scrapy
from scrapy.linkextractors import LinkExtractor
from twisted.internet import defer

import json

from influnc_plus.db.models import Blog
from influnc_plus.filter.keyword_tester import get_tester
from influnc_plus.items import BlogLinkItem
from influnc_plus.util.utils import findRssXmls, getXmlTagParser, str_collapse


def if_path_contains_keyword(path, keywords: list[str]) -> bool:
    for item in keywords:
        if item in path:
            return True
    return False


def if_title_contains_keyword(title, keywords: list[str]) -> bool:
    for item in keywords:
        if item in title:
            return True
    return False


def if_link_points_to_friend_page(link) -> bool:
    url = urlparse(link.url)
    # 检查URL和链入标题, 是否包含特定关键词
    links_keyword = ['friend', 'link']
    title_keyword = ['友情链接', '友链', '朋友', '友人', 'Friend']
    if if_path_contains_keyword(url.path, links_keyword) \
            or if_title_contains_keyword(link.text, title_keyword):
        return True
    else:
        return False


def get_unaccessed_blog():
    return Blog.get(Blog.status == "unknown")


def has_unaccessed_blog():
    return len(Blog.select().where(Blog.status == "unknown")) > 0


def cleanup_database():
    query = Blog.update(status="unknown").where(Blog.status == "pending")
    query.execute()


class BlogsSpider(scrapy.Spider):
    name = "blogs"
    denied_domains = [
        'beian.miit.gov.cn',
        'typecho.org',
        'www.typecho.org',
        'wordpress.org',
        'cn.wordpress.org',
        'bilibili.com'
    ]
    handle_httpstatus_list = [301, 302] # manually handle redirections
    retry_max_count = 5

    def __init__(self, **kwargs):
        self.retries = {}
        self.console_logger = logging.getLogger("info-console")
        self.console_logger.setLevel(logging.INFO)
        # remove all default handlers
        for handler in self.console_logger.handlers:
            self.console_logger.removeHandler(handler)
        # create console handler and set level to info
        console_handle = logging.StreamHandler()
        console_handle.setLevel(logging.INFO)

        # create formatter
        formatter = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y/%m/%d %I:%M:%S")
        console_handle.setFormatter(formatter)

        # now add new handler to logger
        self.console_logger.addHandler(console_handle)
        self.tester = get_tester()
        super().__init__(**kwargs)

    def start_requests(self):
        # unscraped_blogs = Blog.select().where(Blog.status == "unknown").iterator()
        # for item in unscraped_blogs:
        #     url = "https://" + item.domain
        #     self.log("URL: " + url, logging.DEBUG)
        #     yield scrapy.Request(url, callback=self.parse_blog, errback=self.error_handling, cb_kwargs={'src': item})
        while has_unaccessed_blog():
            blog = get_unaccessed_blog()
            blog.status = "pending"
            blog.save()
            url = "https://" + blog.domain
            self.console_logger.info("Yielded item: {}".format(url))
            yield scrapy.Request(url, callback=self.parse_blog, errback=self.error_handling, cb_kwargs={'src': blog})

    def error_handling(self, failure):
        src_blog = failure.request.cb_kwargs['src']
        src_blog.status = "offline"
        src_blog.last_access_time = datetime.now()
        src_blog.save()
        self.console_logger.info("[{}] 不可达，已放弃连接".format(src_blog.title))

    def get_page_title(self, response) -> Tuple[str, str]:
        # Fallback path: og:site_name -> og:title -> HTML title
        og_site_name = response.xpath('//meta[@property="og:site_name"]/@content')
        if len(og_site_name) == 1:
            return str_collapse(og_site_name[0].get()), 'og:site_name'
        og_title = response.xpath('//meta[@property="og:title"]/@content')
        if len(og_title) == 1:
            return str_collapse(og_title[0].get()), 'og:title'
        return str_collapse(response.css('title::text').get()), 'HTML'

    def parse_blog(self, response, **kwargs):
        src_blog = kwargs['src']
        if response.status == 301 or response.status == 302:
            retries = self.retries.setdefault(response.url, 0)
            if retries < self.retry_max_count:
                self.retries[response.url] += 1
                yield response.request.replace(dont_filter = True)
                return
            else:
                # Too many redirects!
                src_blog.status = "dropped"
                src_blog.last_access_time = datetime.now()
                src_blog.save()
                self.console_logger.info("[{}] 重定向次数过多，已丢弃".format(src_blog.domain))
                return
        try:
            m_title = self.get_page_title(response)
            src_blog.title = m_title[0]

            # 尝试获取RSS，这个属性拥有最高的优先级
            potential_rss_tags = findRssXmls(response)
            if len(potential_rss_tags) != 0:
                # data structure: tuple(title, link)
                parseXmlTag = getXmlTagParser(src_blog.title)
                rss_items = list(map(parseXmlTag, potential_rss_tags))
                rss_db_json = json.dumps(rss_items, ensure_ascii=False).encode('utf-8')
                src_blog.rss_json = rss_db_json
                self.console_logger.info("[{}] 已抓取 {} 条 RSS 信息".format(src_blog.title, len(potential_rss_tags)))
            else:
                # If no feed is found, test page title now
                self.console_logger.info("[{}] 没有获取到 RSS 信息".format(src_blog.title))
                flag, keyword = self.tester.test(src_blog.title)
                if flag:
                    self.console_logger.info("[{}] 发现关键词: ----> [{}] <----, 条目已在[抓取后]丢弃".format(src_blog.title, keyword))
                    src_blog.status = "dropped"
                    src_blog.last_access_time = datetime.now()
                    src_blog.save()
                    return

            # Save new title and rss data
            src_blog.save()

            self.console_logger.info("[{}] 正在进入: {}, 标题来源: {}".format(src_blog.title, src_blog.domain, m_title[1]))
            insite_link_extractor = LinkExtractor(allow_domains=[urlparse(response.url).netloc], unique=True)
            has_friend_page = False

            # 获取友链页面
            for link in insite_link_extractor.extract_links(response):
                if if_link_points_to_friend_page(link):
                    self.console_logger.info("[{}] 发现了疑似友链页面:{}".format(src_blog.title, link.url))
                    has_friend_page = True
                    url = response.urljoin(link.url)
                    yield scrapy.Request(url, callback=self.parse_friend_page, cb_kwargs={'src': src_blog})
            if has_friend_page:
                src_blog.status = "online-links"
            else:
                src_blog.status = "online-no-links"
                self.console_logger.info("[{}] 没有找到友链页面".format(src_blog.title))
            src_blog.last_access_time = datetime.now()
            src_blog.save()
        except Exception:
            src_blog.status = "dropped"
            src_blog.last_access_time = datetime.now()
            src_blog.save()
            self.console_logger.warning("[{}] 读取过程出错，放弃连接".format(src_blog.domain))

    def parse_friend_page(self, response, **kwargs):
        src_blog = kwargs['src']
        self.console_logger.info("[{}] 正在解析友链页面".format(src_blog.title))
        ext_link_extractor = LinkExtractor(deny_domains=self.denied_domains + [urlparse(response.url).netloc]
                                           , unique=True)
        for link in ext_link_extractor.extract_links(response):
            url = urlparse(link.url)
            if url.path == "":
                yield BlogLinkItem(url=url, title=link.text, src_blog=src_blog)

    def closed(self, reason):
        query = Blog.update(status="unknown").where(Blog.status == "pending")
        self.console_logger.info("Spider exiting, treating all pending requests as unknown")
        query.execute()
