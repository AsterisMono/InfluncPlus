from csv import writer
from csv import reader
from datetime import datetime

from influnc_plus.db.models import Blog


def import_csv(file_name: str):
    with open(file_name, 'r', encoding='utf8') as read_obj, \
            open('import-result.csv', 'w', newline='') as write_obj:
        csv_reader = reader(read_obj)
        csv_writer = writer(write_obj)
        for row in csv_reader:
            title = row[0]
            domain = row[1]
            blog, created = Blog.get_or_create(domain=domain)
            if created:
                blog.title = title
                blog.status = "unknown"
                blog.last_access_time = datetime.now()
                blog.save()
            row.append('√ 已导入' if created else '× 已存在')
            csv_writer.writerow(row)


if __name__ == '__main__':
    import_csv('chinese-independent-blogs.csv')
