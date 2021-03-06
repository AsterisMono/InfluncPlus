import logging
import re

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


if __name__ == '__main__':
    print(str_collapse("   测 试\n            测试       \n  "))
    print(str_collapse(" Felix's \n cat"+"""
    
    
    hel     lo?
    """))
