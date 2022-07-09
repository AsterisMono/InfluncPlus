from datetime import datetime
from urllib.parse import urlparse

import scrapy
from scrapy.linkextractors import LinkExtractor

from influnc_plus.db.models import Blog
from influnc_plus.items import BlogLinkItem
from influnc_plus.util.utils import str_collapse


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

    def start_requests(self):
        # unscraped_blogs = Blog.select().where(Blog.status == "unknown").iterator()
        # for item in unscraped_blogs:
        #     url = "https://" + item.domain
        #     self.log("URL: " + url, logging.DEBUG)
        #     yield scrapy.Request(url, callback=self.parse_blog, errback=self.error_handling, cb_kwargs={'src': item})
        cleanup_database()
        while has_unaccessed_blog():
            blog = get_unaccessed_blog()
            blog.status = "pending"
            blog.save()
            url = "https://" + blog.domain
            yield scrapy.Request(url, callback=self.parse_blog, errback=self.error_handling, cb_kwargs={'src': blog})

    def error_handling(self, failure):
        src_blog = failure.request.cb_kwargs['src']
        src_blog.status = "offline"
        src_blog.last_access_time = datetime.now()
        src_blog.save()

    def get_page_title(self, response)-> (str, str):
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
        m_title = self.get_page_title(response)
        src_blog.title = m_title[0]
        src_blog.save()
        self.logger.info("[{}] 正在进入: {}, 标题来源: {}".format(src_blog.title, src_blog.domain, m_title[1]))
        insite_link_extractor = LinkExtractor(allow_domains=[urlparse(response.url).netloc], unique=True)
        has_friend_page = False
        for link in insite_link_extractor.extract_links(response):
            if if_link_points_to_friend_page(link):
                self.logger.info("[{}] 发现了疑似友链页面:{}".format(src_blog.title, link.url))
                has_friend_page = True
                url = response.urljoin(link.url)
                yield scrapy.Request(url, callback=self.parse_friend_page, cb_kwargs={'src': src_blog})
        if has_friend_page:
            src_blog.status = "online-links"
        else:
            src_blog.status = "online-no-links"
        src_blog.last_access_time = datetime.now()
        src_blog.save()

    def parse_friend_page(self, response, **kwargs):
        src_blog = kwargs['src']
        self.logger.info("[{}] 正在解析友链页面".format(src_blog.title))
        ext_link_extractor = LinkExtractor(deny_domains=self.denied_domains + [urlparse(response.url).netloc]
                                           , unique=True)
        for link in ext_link_extractor.extract_links(response):
            url = urlparse(link.url)
            if url.path == "":
                yield BlogLinkItem(url=url, title=link.text, src_blog=src_blog)
