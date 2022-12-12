#!/usr/bin/env python3
# -*- coding: utf-8 -*-

name = 'web_2_album'

import cached_url
from bs4 import BeautifulSoup
import export_to_telegraph
from telegram_util import matchKey, cutCaption, getWid, parseDomain, getTitleFromText
from telegram_util import AlbumResult as Result
import readee
import time
import yaml
import sys

IMG_CLASSES = ['f-m-img', 'group-pic', 'image-wrapper', 
	'RichText', 'image-container', 'news_txt', "'article_con'", 
	'photo_wrap', 'hideBeforeLoad', 'slide_container', 'rich_media_content',
	'is-widgets', 'entry-content', 'image-show', 
	'o-noteContentImage__item', 'open-list-post-description',
	'open-list-media-container', 'article-inline-photo',
	'tl_article_content', 'entity-image']

try:
	with open('CREDENTIALS') as f:
		credential = yaml.load(f, Loader=yaml.FullLoader)
	export_to_telegraph.token = credential.get('telegraph_token')
except:
	pass

def getTopic(item):
	topic = item.find('p', class_='topic-say')
	topic = topic and topic.text
	if topic:
		return '【%s】\n\n' % topic
	return ''

def getQuote(item):
	item = BeautifulSoup(str(item), 'html.parser')
	for sub_item in item.find_all('a', class_='reshared_by'):
		sub_item.decompose()
	result = []
	for sub_item in list(item.find_all('blockquote'))[::-1]:
		if not result:
			result = [sub_item]
			continue
		for comment in sub_item:
			comments = [str(comment).strip()]
			break
		for span in sub_item.find_all('span'):
			comments += [span.text.strip().strip(':').strip()] 
		result += ['\n\n【网评】' + comment for comment in comments if len(comment) > 5][::-1]
	# 处理“更多转发...”
	return '<div>%s</div>' % ''.join([str(sub_item) for sub_item in result])

def getTweets(b):
	new_soup = BeautifulSoup("<div></div>", features="html.parser")
	for item in b.findAll('div', class_='content-tweet'):
		new_soup.append(item)
	return new_soup
	
def getCap(b, path):
	wrapper = (b.find('div', class_='weibo-text') or 
		b.find('div', class_='post f') or 
		b.find('div', class_='topic-richtext') or
		b.find('p', id='first', class_='lead') or 
		getTweets(b))
	if 'douban' in path and 'group/topic' in path:
		try:
			title = b.find('td', class_='tablecc').text[3:]
		except:
			if not b.find('title'):
				return ''
			title = b.find('title').text.strip()
		content = (b.find('div', class_='topic-richtext') or 
			b.find('div', class_='topic-content').find('div', class_='topic-content'))
		for item in content.find_all('p'):
			item.append('\n\n')
		for item in content.find_all('div'):
			item.append('\n\n')
		for item in content.find_all('br'):
			item.replace_with('\n\n')
		for item in content.find_all('a'):
			item.decompose()
		return '【%s】\n\n%s' % (getTitleFromText(title), content.text.strip())
	if 'douban' in path:
		wrapper = BeautifulSoup(
			'<div>%s%s</div>' % (getTopic(b), getQuote(b)), 'html.parser')
	if 'zhihu' in path:
		answer = b.find('div', class_='RichContent-inner')
		answer = answer and answer.text.strip()
		if answer:
			return cutCaption(answer, '', 200)
	if not wrapper:
		return ''
	return export_to_telegraph.exportAllInText(wrapper)

def isWeiboArticle(path):
	return matchKey(path, ['card', 'ttarticle']) and 'weibo.c' in path

def isValidSrc(candidate):
	return candidate and not matchKey(candidate, ['data:image', '/images/1px.png'])

def getValidSrc(*candidates):
	for candidate in candidates:
		if isValidSrc(candidate):
			return candidate

def getSrc(img, path):
	src = getValidSrc(img.get('data-full'), img.get('data-original'), 
		img.get('data-actualsrc'), img.get('src'), img.get('data-src'))
	src = src and src.strip()
	if not src:
		return 
	if not img.parent or not img.parent.parent:
		return 
	if 'reddit' in path:
		if img.parent.name != 'a':
			return
		return img.parent['href']
	if 'blog.boxun' in path:
		return '/'.join(path.split('/')[:-1] + [src])
	if isWeiboArticle(path) and 'sinaimg' in src:
		return src
	wrapper = img.parent.parent
	if 'detail' in sys.argv:
		print(str(wrapper.get('class')))
	if matchKey(str(wrapper.get('class')) or '', IMG_CLASSES):
		return src
	return

def enlarge(src, img):
	if not src:
		return None
	src = src.replace('/m/', '/l/')
	if 'animate' in img.parent.get('class', ''):
		src = '.'.join(src.split('.')[:-1]) + '.mp4'
	return src

def withDomain(path, x):
	if x.startswith('//'):
		return 'https:' + x
	if 'slideshare' in x:
		x = x.split('?')[0]
	if x and x[0] == '/':
		return parseDomain(path) + x
	return x

def getImgs(b, path):
	raw = [enlarge(getSrc(img, path), img) for img in b.find_all('img')]
	return [withDomain(path, x) for x in raw if x]

def getVideo(b):
	for video in b.find_all('video'):
		if not video.parent or not video.parent.parent:
			continue
		wrapper = video.parent.parent
		source = video.find('source')
		source = source and source['src']
		if source:
			return source
		if not matchKey(str(wrapper.get('id')), ['video_info']):
			continue
		return video['src']

def getContent(path, force_cache=False):
	if isWeiboArticle(path):
		new_url = ('https://card.weibo.com/article/m/aj/detail?id=' + 
			getWid(path) + '&_t=' + str(int(time.time())))
		json = yaml.load(
			cached_url.get(new_url, headers={'referer': path}, force_cache=force_cache), 
			Loader=yaml.FullLoader)
		return '<div><title>%s</title>%s</div>' % (json['data']['title'], json['data']['content'])
	return cached_url.get(path, force_cache=force_cache)

def get(path, force_cache=False, content = None):
	path = path.replace('m.douban.com', 'www.douban.com')
	content = content or getContent(path, force_cache=force_cache)
	b = BeautifulSoup(str(content), features='html.parser')
	if 'threadreaderapp.com' in path:
		b = b.select('div.container.narrow')[0]
	result = Result()
	result.imgs = getImgs(b, path)
	result.cap = getCap(b, path)
	result.video = getVideo(b)
	result.url = path
	return result