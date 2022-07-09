import re

rex = re.compile(r'\W+')


def str_collapse(string: str) -> str:
    return rex.sub(' ', string).strip()


if __name__ == '__main__':
    print(str_collapse("   测 试\n            测试       \n  "))
