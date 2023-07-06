# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json
import os
import time

import pymysql
from itemadapter import ItemAdapter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from XPC_Scrapy.items import XpcBaseInfoItem, XpcCommentItem, XpcVideoUrlItem


class XpcScrapyPipeline:
	def get_login_cookie(self, phone_number, password):
		options = Options()
		options.add_argument('--headless')
		browser = webdriver.Chrome(options=options)
		browser.get("https://passport.xinpianchang.com/login")

		wait = WebDriverWait(browser, 10)  # Set the waiting time to 10 seconds.

		# Wait for the form to appear and enter the data.
		phone_input = wait.until(EC.visibility_of_element_located((By.XPATH, '//input[@type="tel"]')))
		phone_input.send_keys(phone_number)

		password_input = wait.until(EC.visibility_of_element_located((By.XPATH, '//input[@type="password"]')))
		password_input.send_keys(password)

		login_btn = wait.until(EC.visibility_of_element_located((By.XPATH, '//button[@type="submit"]')))
		login_btn.click()

		# Wait for the page to load, and when the URL of the page is converted into a profile page, obtain the cookie.
		while True:
			if browser.current_url == 'https://passport.xinpianchang.com/settings':
				cookies = browser.get_cookies()
				browser.close()
				break

		# Convert to cookies available in requests and return.
		return {c['name']: c['value'] for c in cookies}

	def get_db_connection(self, host, user, password, port, database):
		"""
		Attempt to obtain a database connection,
		if unsuccessful, set the connect property to None.
		"""
		try:
			self.connect = pymysql.Connection(
				host=host,
				port=port,
				user=user,
				password=password,
				database=database,
				charset='utf8mb4'
			)
		except Exception as e:
			self.connect = None

	def open_spider(self, spider):
		# Read the configuration file.
		with open('./profile.json', 'r', encoding='utf-8') as file:
			data = json.load(file)

		# Obtain and save the cookies when logged.
		phone_number = data.get('xpc_account').get('phone_number')
		password_xpc = data.get('xpc_account').get('password')

		with open('./cookies', 'w', encoding='utf-8') as file:
			data_str = json.dumps(self.get_login_cookie(phone_number, password_xpc))
			file.write(data_str)

		spider.logger.info('Cookie obtained successfully.')

		# Obtain database connection.
		host = data.get('localdb').get('host')
		user = data.get('localdb').get('user')
		password_db = data.get('localdb').get('password')
		port = data.get('localdb').get('port')
		database = data.get('localdb').get('database')
		self.get_db_connection(host, user, password_db, port, database)

		# Determine whether the connection acquisition was successful.
		# If it fails, an exception is thrown and the program is terminated.
		if self.connect:
			spider.logger.info('Database connection successful!')
		else:
			spider.logger.critical('Database connection failed!')
			raise Exception('Database connection failed!')

	def close_spider(self, spider):
		os.remove('./cookies')
		spider.logger.info('The cookie has been deleted.')

		if self.connect:
			self.connect.close()

		spider.logger.info('The crawler has completed running.')

	def process_item(self, item, spider):
		curser = self.connect.cursor()

		try:
			if isinstance(item, XpcBaseInfoItem):
				article_id = item.get('article_id')
				title = item.get('title')
				like = item.get('like')
				collection = item.get('collection')
				insert_sql = f"INSERT INTO video_base_info (article_id, title, like_count, collection_count) VALUES ({article_id}, '{title}', '{like}', '{collection}');"
			elif isinstance(item, XpcCommentItem):
				comment_id = item.get('comment_id')
				timestamp = item.get('timestamp')
				content = item.get('content')
				article_id = item.get('article_id')
				insert_sql = f"INSERT INTO comment (comment_id, article_id, content, timestamp) VALUES ({comment_id}, {article_id}, '{content}', '{timestamp}');"
			elif isinstance(item, XpcVideoUrlItem):
				article_id = item.get('article_id')
				quality = item.get('quality')
				url = item.get('url')
				insert_sql = f"INSERT INTO video_url (article_id, quality, url) VALUES ({article_id}, '{quality}', '{url}');"

			curser.execute(insert_sql)
		except Exception as e:
			spider.logger.critical(e)
			self.connect.rollback()
		else:
			self.connect.commit()

		return item
