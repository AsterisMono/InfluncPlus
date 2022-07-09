from urllib import parse

from peewee import *
import datetime

db = SqliteDatabase('influnc_plus/db/database.db')

class BaseModel(Model):
    class Meta:
        database = db


class Blog(BaseModel):
    domain = CharField()
    title = CharField()
    status = CharField()  # online-links, online-no-links, offline or unknown
    last_access_time = DateTimeField()


class Link(BaseModel):
    src_blog = ForeignKeyField(Blog, backref="links_out")
    dst_blog = ForeignKeyField(Blog, backref="links_in")


def create_tables():
    db.connect()
    db.create_tables([Blog, Link])

def prepare_initial_data():
    skyblond = Blog(domain="skyblond.info", title="天空Blond", status="unknown", last_access_time=datetime.datetime.now())
    himiku = Blog(domain="himiku.com", title="初之音", status="unknown", last_access_time=datetime.datetime.now())
    skyblond.save()
    himiku.save()

if __name__ == '__main__':
    create_tables()
    prepare_initial_data()
