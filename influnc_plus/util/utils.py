import re

rex = re.compile(r'\W+')


def str_collapse(string: str) -> str:
    return rex.sub(' ', string)


if __name__ == '__main__':
    print(str_collapse("测试\n            测试       \n"))
