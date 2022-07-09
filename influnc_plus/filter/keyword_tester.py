import logging
import os

import ahocorasick

keyword_file_name = 'influnc_plus/filter/keyword_list.txt'


def make_ac(ac, word_set):
    for word in word_set:
        ac.add_word(word, word)
    return ac


def generate_automaton():
    with open(keyword_file_name, 'r', encoding="utf8") as f:
        keyword_list = f.readlines()
        keyword_list = list(map(lambda x: x.replace('\n', ''), keyword_list))
    ac = ahocorasick.Automaton()
    ac = make_ac(ac, keyword_list)
    ac.make_automaton()
    return ac


class Tester:
    def __init__(self):
        self.ac = generate_automaton()
        self._cached_stamp = os.stat(keyword_file_name).st_mtime
        self.logger = logging.getLogger('info-console')

    def update(self) -> bool:
        stamp = os.stat(keyword_file_name).st_mtime
        if stamp != self._cached_stamp:
            self._cached_stamp = stamp
            # Keyword list has changed
            self.ac = generate_automaton()
            return True
        return False

    def test(self, haystack: str) -> (bool, str):
        if_updated = self.update()
        if if_updated:
            self.logger.info("[过滤器] 过滤器黑名单已经改变，正在更新...")
        for item in self.ac.iter(haystack):
            return True, item[1]
        return False, ''


tester = Tester()


def get_tester():
    return tester


if __name__ == '__main__':
    tester = Tester()
    print(tester.test("北京VPS服务"))
    print(tester.test("上海信息网"))
    print(tester.test("个人小站"))
