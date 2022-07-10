from influnc_plus.db.models import Blog
from influnc_plus.filter.keyword_tester import get_tester


def filter():
    tester = get_tester()
    for item in Blog.select().iterator():
        flag, keyword = tester.test(item.title)
        if flag:
            print("[{}] 发现关键词: ----> [{}] <----, 条目已在[离线处理]丢弃".format(item.title, keyword))
            item.status = "dropped"
            item.save()


if __name__ == '__main__':
    filter()
