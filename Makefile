resetdb:
	rm influnc_plus/db/database.db && python influnc_plus/db/models.py
run:
	scrapy runspider influnc_plus/spiders/blogs_spider.py --logfile log.txt --loglevel INFO 
debug:
	scrapy runspider influnc_plus/spiders/blogs_spider.py --logfile log.txt --loglevel DEBUG 
venv:
	virtualenv .venv && pip install -r requirements.txt
