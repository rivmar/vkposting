# -*- coding: utf-8 -*-
import logging
import pickle
import time
import threading
import queue
import vk
from configparser import ConfigParser, Error
from tkinter import Tk, Frame, LEFT, WORD, scrolledtext, ttk, messagebox, NO, END, RAISED, VERTICAL, HORIZONTAL, N, S, E, W

common_logger = logging.getLogger(__name__)


class ThreadLogger(threading.Thread):

	def __init__(self, name):
		super().__init__()
		self._stop_event = threading.Event()
		self.logger = logging.getLogger(name)

	def debug(self, *args):
		self.logger.debug(*args)

	def info(self, *args):
		self.logger.info(*args)

	def warning(self, *args):
		self.logger.warning(*args)

	def error(self, *args):
		self.logger.error(*args)

	def critical(self, *args):
		self.logger.critical(*args)

	def addHandler(self, handler):
		self.logger.addHandler(handler)

	def setLevel(self, level):
		self.logger.setLevel(level)

	def run(self):
		self.logger.debug('Clock started')
		previous = -1
		while not self._stop_event.is_set():
			time.sleep(1)

	def stop(self):
		self._stop_event.set()

publish_logger = ThreadLogger('publish_logger')
rollback_logger = ThreadLogger('rollback_logger')
cleanup_logger = ThreadLogger('cleanup_logger')

publish_logger.start()
rollback_logger.start()
cleanup_logger.start()


class QueueHandler(logging.Handler):
	def __init__(self, log_queue):
		super().__init__()
		self.log_queue = log_queue

	def emit(self, record):
		self.log_queue.put(record)


class ConsoleWindow:
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):
        self.frame = frame
        # Create a ScrolledText wdiget
        self.scrolled_text = scrolledtext.ScrolledText(frame, state='disabled', height=12)
        self.scrolled_text.grid(row=0, column=0, sticky=(N, S, W, E))
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)
        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
        # Autoscroll to the bottom
        self.scrolled_text.yview(END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)


class MainWindow(Tk):
	TEXT = 'text'
	IMAGES = 'images'
	GROUPS = 'groups'
	BOARDS = 'boards'

	RUSSIAN_NAMES = {
		TEXT: 'Текст объявления',
		IMAGES: 'Прикрепленные изображения', 
		GROUPS: 'ID групп (действия на стене группы)', 
		BOARDS: 'ID обсуждений',
	}

	DATA_FILE = 'data.pickle'
	RESULT_FILE = 'last_result.pickle'

	def __init__(self):
		try:
			self.init_vk()
		except Error as error:
			common_logger.error('Incorrect settings configuration: {}'.format(error))
			exit()
		self.saved_data = self.get_saved_data()
		super(MainWindow, self).__init__(className='Публикация объявлений')

		self.notebook = ttk.Notebook()
		self.notebook.grid()
		self.frame_publish = ttk.PanedWindow(self.notebook, orient=HORIZONTAL)
		self.frame_publish.grid()
		self.frame_rollback = ttk.PanedWindow(self.notebook, orient=HORIZONTAL)
		self.frame_rollback.grid()
		self.frame_cleanup = ttk.PanedWindow(self.notebook, orient=HORIZONTAL)
		self.frame_cleanup.grid()
		self.text_label, self.text_textbox = self.create_text_complex(self.frame_publish, self.TEXT, 5, 0)
		self.images_label, self.images_textbox = self.create_text_complex(self.frame_publish, self.IMAGES, 2, 1) # ToDo: Add help
		self.groups_label, self.groups_textbox = self.create_text_complex(self.frame_publish, self.GROUPS, 2, 2) # ToDo: Add help
		self.boards_label, self.boards_textbox = self.create_text_complex(self.frame_publish, self.BOARDS, 2, 3) # ToDo: Add help
		
		self.publish_btn = ttk.Button(self.frame_publish, text="Опубликовать", command=self.publish)
		self.publish_btn.grid(row=9, column=1)

		self.publish_console = self.add_console(self.frame_publish, 10)
		publish_logger.addHandler(self.publish_console.queue_handler)
		publish_logger.setLevel(logging.INFO)

		self.rollback_label = ttk.Label(
			self.frame_rollback, 
			text='Здесь вы можете откатить результаты последней публикации.', 
			justify=LEFT,
			padding=20,
			)
		self.rollback_label.grid(row=1, column=1)
		self.rollback_btn = ttk.Button(self.frame_rollback, text="Откатить все нажитое непосильным трудом!", command=self.rollback)
		self.rollback_btn.grid(row=2, column=1)

		self.rollback_console = self.add_console(self.frame_rollback, 10)
		rollback_logger.addHandler(self.rollback_console.queue_handler)
		rollback_logger.setLevel(logging.INFO)

		self.cleanup_label = ttk.Label(self.frame_cleanup, text='Добавьте головной боли товарищу майору.\nУдалите все старые объявления', justify=LEFT)
		self.cleanup_label.grid(row=1, column=1) 
		self.cleanup_groups_label, self.cleanup_groups_textbox = self.create_text_complex(self.frame_cleanup, self.GROUPS, 2, 2) # ToDo: Add help
		self.cleanup_boards_label, self.cleanup_boards_textbox = self.create_text_complex(self.frame_cleanup, self.BOARDS, 2, 3) # ToDo: Add help
		self.cleanup_btn = ttk.Button(self.frame_cleanup, text="Удалить", command=self.cleanup)
		self.cleanup_btn.grid(row=9, column=1) 

		self.cleanup_console = self.add_console(self.frame_cleanup, 10)
		cleanup_logger.addHandler(self.cleanup_console.queue_handler)
		cleanup_logger.setLevel(logging.INFO)


		self.notebook.add(self.frame_publish, text='Публикация')
		self.notebook.add(self.frame_rollback, text='Откат')
		self.notebook.add(self.frame_cleanup, text='Очистка')
		self.mainloop()

	def init_vk(self):
		self.config = ConfigParser()
		self.config.read_file(open('../settings.ini'))
		self.APIV = self.config.get('VKMain', 'VK_APIVersion')
		self.my_id = self.config.getint('VKMain', 'VK_MY_USER_ID')
		VK_TOKEN = self.config.get('VKMain', 'VK_ACCESS_TOKEN')
		session = vk.Session(access_token=VK_TOKEN)
		self.api = vk.API(session)

	def get_saved_data(self):
		try:
			with open(self.DATA_FILE, 'rb') as f:
				saved_data = pickle.load(f)
		except FileNotFoundError:
			saved_data = {self.TEXT: [], self.IMAGES: [], self.GROUPS: [], self.BOARDS: []}
		return saved_data

	def create_text_complex(self, frame, title, heigth, index):
		label = ttk.Label(frame, text=self.RUSSIAN_NAMES[title], justify=LEFT)
		textbox = scrolledtext.ScrolledText(frame, wrap=WORD, height=heigth)
		if self.saved_data[title] and frame is self.frame_publish:
			textbox.insert(END, self.saved_data[title][-1])
		label.grid(row=index * 2 + 1, column=1)
		textbox.grid(row=index * 2 + 2, column=1)
		return label, textbox

	def add_console(self, frame, row):
		console_frame = ttk.Labelframe(frame, text="Console")
		console_frame.columnconfigure(0, weight=1)
		console_frame.rowconfigure(0, weight=1)
		console_frame.grid(row=row, column = 1)
		return ConsoleWindow(console_frame)

	def data_get_and_save(self, widget, title):
		text = widget.get("1.0",'end-1c').strip()
		if text not in self.saved_data[title]:
			save = messagebox.askyesno('Данные изменены', 'Поле "{}" изменено. Сохранить данные?'.format(self.RUSSIAN_NAMES[title]))
			if save:
				self.saved_data[title].append(text)
		setattr(self, title, text)


	def publish(self):
		self.data_get_and_save(self.text_textbox, self.TEXT)
		self.data_get_and_save(self.images_textbox, self.IMAGES)
		self.data_get_and_save(self.groups_textbox, self.GROUPS)
		self.data_get_and_save(self.boards_textbox, self.BOARDS)
		if self.saved_data != self.get_saved_data():
			with open(self.DATA_FILE, 'wb') as f:
				pickle.dump(self.saved_data, f)
		self.result = {self.GROUPS: [], self.BOARDS: []}
		self.publish_to_walls()
		self.publish_to_boards()
		with open(self.RESULT_FILE, 'wb') as f:
				pickle.dump(self.result, f)
		messagebox.showinfo(
			'Публикация завершена.',
			'Вы можете закрыть окно программы'
			)

	def publish_to_walls(self):
		for group in self.groups.split(','):
			time.sleep(5)
			group = group.strip()
			if group:
				group = self.get_group_id(group)
				publish_logger.info('Adding to wall %s', group)
				group = '-{}'.format(group)
				try:
					result = self.api.wall.post(owner_id=group, message=self.text, attachments=self.images, v=self.APIV)
					self.result[self.GROUPS].append((group, result['post_id']))
					publish_logger.info('Done')
				except vk.exceptions.VkAPIError as error:
					publish_logger.error('Vk does not accept some data. Group: {} Error: {}'.format(group, error))

	def get_group_id(self, group):
		response = self.api.utils.resolveScreenName(screen_name=group, v=self.APIV)
		return response['object_id']

	def publish_to_boards(self):
		for group_board in self.boards.split(','):
			if group_board.strip():
				group, board = group_board.strip().split('_')
				if self.get_board_messages(group, board):
					time.sleep(1)
					continue
				time.sleep(5)
				publish_logger.info('Adding to board %s', group_board)
				try:
					result = self.api.board.createComment(group_id=group, topic_id=board, message=self.text, attachments=self.images, v=self.APIV)
					self.result[self.BOARDS].append((group, board, result))
					publish_logger.info('Done')
				except vk.exceptions.VkAPIError as error:
					publish_logger.error('Vk does not accept some data. Error: {}'.format(error))
				
	def get_board_messages(self, group, board, offset=0, count=20, full=False):
		response = self.api.board.getComments(group_id=group, topic_id=board, sort='desc', offset=offset, count=count, v=self.APIV)
		messages = response.get('items')
		if full:
			return messages
		authors = [message.get('from_id') for message in messages]
		if self.my_id in authors:
			publish_logger.info('There is my records in last 20 messages in %s_%s, skipping...', group, board)
			return True
		return False

	def rollback(self):
		rollback_logger.addHandler(self.rollback_console.queue_handler)
		try:
			with open(self.RESULT_FILE, 'rb') as f:
				last_result = pickle.load(f)
		except (FileNotFoundError, EOFError):
			messagebox.showinfo(
			'Старый результат не найден .',
			'Возможные причины:\n1) вы ни разу не запускали публикацию\n2) файл был удален, переименован или перенесен\n3) программа была перенесена, а файл остался на старом месте'
			)
			return
		for group, post in last_result[self.GROUPS]:
			time.sleep(5)
			try:
				rollback_logger.info('Removing from wall %s', group)
				result = self.api.wall.delete(owner_id=group, post_id=post, v=self.APIV)
				if result == 1:
					rollback_logger.info('Done')
				else:
					rollback_logger.error(response)
			except vk.exceptions.VkAPIError as error:
					rollback_logger.error('Vk does not accept some data. Error: {}'.format(error))
		for group, board, post in last_result[self.BOARDS]:
			time.sleep(5)
			try:
				rollback_logger.info('Removing from board %s %s', group, board)
				result = self.api.board.deleteComment(group_id=group, topic_id=board, comment_id=post, v=self.APIV)
				if result == 1:
					rollback_logger.info('Done')
				else:
					rollback_logger.error(response)
			except vk.exceptions.VkAPIError as error:
					rollback_logger.error('Vk does not accept some data. Error: {}'.format(error))
		messagebox.showinfo('','Удаление завершено')

	def cleanup(self):
		cleanup_logger.addHandler(self.cleanup_console.queue_handler)
		groups = self.cleanup_groups_textbox.get("1.0",'end-1c').strip()
		boards = self.cleanup_boards_textbox.get("1.0",'end-1c').strip()
		if groups:
			for group in groups.split(','):
				group = self.get_group_id(group)
				offset = 0
				while True:
					response = self.api.wall.get(owner_id='-{}'.format(group), offset=offset, count=100, filter='others', v=self.APIV)
					posts = response['items']
					if not posts:
						break
					for post in posts:
						if post['from_id'] == self.my_id:
							time.sleep(5)
							cleanup_logger.info('Removing from group: %s id: %s', group, post['id'])
							result = self.api.wall.delete(owner_id='-{}'.format(group), post_id=post['id'], v=self.APIV)
							if result == 1:
								cleanup_logger.info('Done')
							else:
								cleanup_logger.error(response)
					offset += 100
		if boards:
			for group_board in boards.split(','):
				group, board = group_board.strip().split('_')
				offset = 0
				my_messages = []
				while True:
					messages = self.get_board_messages(group, board, offset, count=100, full=True)
					offset += 100
					if not messages:
						break
					for message in messages:
						if message['from_id'] == self.my_id:
							time.sleep(5)
							cleanup_logger.info('Removing from group: %s board: %s id: %s', group, board, message['id'])
							result = self.api.board.deleteComment(group_id=group, topic_id=board, comment_id=message['id'], v=self.APIV)
							if result == 1:
								cleanup_logger.info('Done')
							else:
								cleanup_logger.error(response)
		messagebox.showinfo('', 'Очистка завершена')


if __name__ == '__main__':
	window = MainWindow()