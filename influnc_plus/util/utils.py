import logging
import re

rex = re.compile(r'\W+')


def str_collapse(string: str) -> str:
    try:
        return rex.sub(' ', string).strip()
    except TypeError:
        logging.getLogger().error("[正则] 处理{}时出错".format(string))
        return string


if __name__ == '__main__':
    print(str_collapse("   测 试\n            测试       \n  "))
