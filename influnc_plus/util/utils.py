import logging
import re
from typing import Tuple
import bs4
from bs4 import BeautifulSoup as soup
import requests

rex = re.compile(r'\s{2,}')


def str_collapse(string: str) -> str:
    try:
        return rex.sub(' ', string).strip()
    except TypeError:
        logging.getLogger("info-console").error("[正则] 处理{}时出错".format(string))
        if string is None:
            return ''
        else:
            return string

rss_types = [
        'application/rss+xml',
        'application/atom+xml',
        'application/rdf+xml',
        'application/rss',
        'application/atom',
        'application/rdf',
        'text/rss+xml',
        'text/atom+xml',
        'text/rdf+xml',
        'text/rss',
        'text/atom',
        'text/rdf',
        'application/feed+json',
    ]
rss_link_regex = re.compile(r"\/(feed|rss|atom)(\.(xml|rss|atom))?$")

def filter_rss_url(el: bs4.element.Tag) -> bool:
    is_valid_link_element = el.name == "link" and el.has_attr("type") \
            and el.attrs["type"] in rss_types and el.has_attr("href")
    is_valid_a_element = el.name == "a" and el.has_attr("href") \
            and rss_link_regex.match(el.attrs["href"]) is not None
    return is_valid_link_element or is_valid_a_element 

def findRssXmls(response) -> list[bs4.element.Tag]:
    try:
        html = soup(response.text)
        potential_feed_tags = html.find_all(filter_rss_url)
        return potential_feed_tags
    except:
        return []

def getXmlTagParser(default_title: str):
    def parseXmlTag(tag: bs4.element.Tag):
        title = tag.attrs["title"] if tag.has_attr("title") else default_title
        url = tag.attrs["href"]
        return {
                "title": title,
                "url": url
            } 
    return parseXmlTag


if __name__ == '__main__':
    # print(str_collapse("   测 试\n            测试       \n  "))
    # print(str_collapse(" Felix's \n cat"+"""
    # 
    # 
    # hel     lo?
    # """))
    url = "https://www.skyblond.info/"
    findRssXmls(requests.get(url))
    pass
