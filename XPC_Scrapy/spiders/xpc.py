import datetime
import json

import scrapy
from bs4 import BeautifulSoup

from XPC_Scrapy.items import XpcBaseInfoItem, XpcCommentItem, XpcVideoUrlItem


class XpcSpider(scrapy.Spider):
	name = 'xpc'
	xpc_api_url = 'https://www.xinpianchang.com/api/xpc'

	allowed_domains = [
		'www.xinpianchang.com'
	]

	start_urls = [
		'https://www.xinpianchang.com/discover/article-1-0-all-all-0-0-hot?page=11'
	]

	def parse(self, response):
		# Build BS4 objects, obtain titles and the links to detail pages.
		soup = BeautifulSoup(response.text, "html.parser")

		for movie_div in soup.select('main > div > div:nth-child(3) > div'):
			title = movie_div.select_one('div > div > div:nth-child(2) > div > a > h2').text
			detail_page_url = movie_div.select_one('div > div > div:nth-child(2) > div > a').attrs['href']

			# Initiate a request for the details page.
			yield scrapy.Request(url=detail_page_url, meta={'title': title}, callback=self.parse_detail)

		# Crawling multiple pages of data
		page_no = int(response.url[response.url.rfind('=') + 1:])
		if page_no <= 15:
			next_page_url = response.url[:response.url.rfind('=') + 1] + str(int(page_no) + 1)
			yield scrapy.Request(url=next_page_url, callback=self.parse)

	def parse_detail(self, response):
		# Data extract.
		article_id = response.url[response.url.rfind('a') + 1:]
		title = response.meta.get('title')
		like = response.xpath('//button[@aria-label="点赞"]/span/text()').get()
		collection = response.xpath('//button[@aria-label="收藏"]/span/text()').get()

		# Seal the data.
		item = XpcBaseInfoItem()
		item['article_id'] = article_id
		item['title'] = title
		item['like'] = like
		item['collection'] = collection

		yield item

		# Build first comment url and initiate a request for the comment.
		first_comment_url = f'{self.xpc_api_url}/comments/article/v2?article_id={article_id}&page=1'
		yield scrapy.Request(url=first_comment_url, meta={'article_id': article_id}, callback=self.parse_movie_comments)

		# Build video play url and initiate a request for the play url.
		video_data = json.loads(response.xpath('//script[@id="__NEXT_DATA__"]/text()').get())
		video_data_detail = video_data.get('props').get('pageProps').get('detail')

		app_key = video_data_detail.get('video').get('appKey')
		video_library_id = video_data_detail.get('video_library_id')

		video_resource_url = f'https://mod-api.xinpianchang.com/mod/api/v2/media/{video_library_id}?appKey={app_key}'
		yield scrapy.Request(url=video_resource_url, meta={'article_id': article_id}, callback=self.parse_video_urls,
							 dont_filter=True)

	def parse_movie_comments(self, response):
		# Data extract from current page.
		article_id = response.meta.get('article_id')

		data = response.json()
		for comment_data in data.get('data').get('list'):
			comment_id = comment_data.get('id')
			content = comment_data.get('content').strip()

			time_data = comment_data.get('addtime')
			dt_obj = datetime.datetime.fromtimestamp(time_data)
			timestamp = dt_obj.strftime('%Y-%m-%d %H:%M:%S')

			# Seal the data.
			item = XpcCommentItem()
			item['comment_id'] = comment_id
			item['timestamp'] = timestamp
			item['content'] = content
			item['article_id'] = article_id

			yield item

		# Request next page.
		next_page_url = data.get('data').get('next_page_url')
		if next_page_url:
			next_page_url = self.xpc_api_url + data.get('data').get('next_page_url')
			yield scrapy.Request(url=next_page_url, meta={'article_id': article_id}, callback=self.parse_movie_comments)

	def parse_video_urls(self, response):
		# Data extract
		article_id = response.meta.get('article_id')

		data = response.json()
		for resource in data.get('data').get('resource').get('progressive'):
			quality = resource.get('quality')
			video_url = resource.get('url')

			# Seal the data.
			item = XpcVideoUrlItem()
			item['article_id'] = article_id
			item['quality'] = quality
			item['url'] = video_url
			yield item
