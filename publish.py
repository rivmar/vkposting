# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals, absolute_import
import argparse
import ConfigParser
import time
import logging
from functools import wraps

import vk

logging.basicConfig(filename='../log.txt', level=logging.INFO)
logger = logging.getLogger()


parser = argparse.ArgumentParser(description='Posting to vk walls and boards.')
parser.add_argument('--section', default='Test', help='Section name')
section = parser.parse_args().section

def catcher(func):
	@wraps(func)
	def wrapper(*args, **kwds):
		try:
			result = func(*args, **kwds)
			return result
		except ConfigParser.Error as error:
			logger.error('Incorrect settings configuration: %s', error)
			exit()
		except vk.exceptions.VkAPIError as error:
			logger.error('Vk does not accept some data. Error: %s', error)
			exit()
		except IOError as error:
			logger.error('Incorrect file path. Error: %s', error)
			exit()
	return wrapper


class Publisher:

	def __init__(self, section='Russia'):
		self.init_vk()
		self.section = section
		self.get_pathes()
		self.get_data_from_files()

	@catcher
	def publish_to_walls(self):
		for group in self.groups.split(','):
			group = group.strip()
			if group:
				logger.info('Add record to %s', group)
				group = self.get_group_id(group)
				group = '-{}'.format(group)
				result = self.api.wall.post(owner_id=group, message=self.text, attachments=self.images, v=self.APIV)
				logger.info('Result: %s', result)
				time.sleep(1)

	@catcher
	def publish_to_boards(self):
		for group_board in self.boards.split(','):
			if group_board.strip():
				group, board = group_board.strip().split('_')
				if self.get_board_messages(group, board):
					continue
				logger.info('Add record to board %s', group_board)
				result = self.api.board.createComment(group_id=group, topic_id=board, message=self.text, attachments=self.images, v=self.APIV)
				logger.info('Result: %s', result)
				time.sleep(5)

	@catcher
	def get_group_id(self, group):
		response = self.api.utils.resolveScreenName(screen_name=group, v=self.APIV)
		return response['object_id']

	@catcher
	def get_board_messages(self, group, board):
		response = self.api.board.getComments(group_id=group, topic_id=board, sort='desc', v=self.APIV)
		messages = response.get('items')
		authors = [message.get('from_id') for message in messages]
		if self.my_id in authors:
			logging.info('There is my records in last 20 messages in %s_%s, skipping...', group, board)
			return True
		return False

	@catcher
	def init_vk(self):
		self.config = ConfigParser.SafeConfigParser()
		self.config.readfp(open('../settings.ini'))
		self.APIV = self.config.get('VKMain', 'VK_APIVersion')
		self.my_id = self.config.getint('VKMain', 'VK_MY_USER_ID')
		VK_TOKEN = self.config.get('VKMain', 'VK_ACCESS_TOKEN')
		session = vk.Session(access_token=VK_TOKEN)
		self.api = vk.API(session)

	@catcher
	def get_pathes(self):
		self.text_file = self.config.get(self.section, 'TEXT_FILE')
		self.groups_file = self.config.get(self.section, 'GROUPS_FILE')
		self.images_file = self.config.get(self.section, 'IMAGES_FILE')
		self.boards_file = self.config.get(self.section, 'BOARDS_FILE')

	def get_data_from_files(self):
		self.text = self.get_data_from_file(self.text_file)
		self.groups = self.get_data_from_file(self.groups_file)
		self.images = self.get_data_from_file(self.images_file)
		self.boards = self.get_data_from_file(self.boards_file)


	@catcher
	def get_data_from_file(self, file):
		with open(file, 'r') as f:
			text = f.read()
		return text



publisher = Publisher(section)
publisher.publish_to_walls()
publisher.publish_to_boards()

exit()