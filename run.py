#!/usr/bin/python3

import requests
import json
import atexit
import time
import unicodedata
import random
import os
from tokens import *
from game import *

def get_name(user):
	if ('username' in user):
		return user['username']
	else:
		return user['first_name'] + " " + user['last_name']

def from_json(s):
	s = s.replace("'", "\"")
	return json.loads(s)

def get_params(s, command):
	pos = s.find(command) + len(command)
	s = s[pos:]
	return s.split()

def get_command(s):
	pos = s.find("/") + 1
	if (pos == 0):
		return ""
	res = "/"
	while (pos < len(s) and unicodedata.category(s[pos]) in ('Ll', 'Pc')):
		res += s[pos]
		pos += 1
	return res

def suffix(s, command):
	pos = s.find(command) + len(command)
	return s[min(pos + 1, len(s)):]

WRONG_MESSAGE_RESPONSE = "Я тебя не понимаю :("
HELP_MESSAGE = "Хэлп"
CANT_CHANGE_NAME_MESSAGE = "Менять имя можно только тогда, когда этого никто не видит"
WRONG_CHARECTERS_IN_NAME_MESSAGE = "Имя может содержать только буквы и цифры"
ALREADY_IN_GAME_MESSAGE = "Сначала выйди из текущей игры (/leave)"

def text_message(text):
	return {'command' : 'sendMessage', 'text' : text}

def markdown_message(text):
	return {'command' : 'sendMessage', 'parse_mode' : 'Markdown', 'text' : text}

def correct(s):
	for c in s:
		cat = unicodedata.category(c)
		if cat not in ('Ll', 'Lu', 'Lo', 'Nd', 'Zs'):
			return 0
	return 1

class chat_with_bot:

	def __init__(self, _id, _url, _token, _name):
		self.id = _id
		self.rev = 0
		self.url = _url
		self.token = _token
		self.name = _name
		self.game_id = -1
		self.waiting_for_file = 0

	def setparams(self, string):
		params = from_json(string)
		self.name = params['name']
		#self.game_id = params['game_id']!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

	def __str__(self):
		params = {'name' : self.name, 'game_id' : self.game_id}
		return str(params)


class game_group:

	def __init__(self, _id, _admin_id, _is_private, _params):
		self.game_id = _id
		self.players = [_admin_id]
		self.whose_turn = -1
		self.last_turn_time = -1
		self.is_private = _is_private
		self.params = _params
		self.filename = ""
		self.players_cnt = 1
		self.tl = DEFALUT_TL
		self.started = 0

	def join(self, player_id):
		self.players.append(player_id)
		self.players_cnt += 1

	def leave(self, player_id):
		self.players_cnt -= 1
		if (self.whose_turn == -1):
			self.players.remove(player_id)
		else:
			for i in range(len(self.players)):
				if (self.players[i] == player_id):
					self.players[i] = 0

	def isadmin(self, player_id):
		if (self.players[0] == player_id):
			return 1
		else:
			return 0

	def make_next_turn(self):
		self.whose_turn = (self.whose_turn + 1) % self.all_players_cnt
		self.last_turn_time = time.time()

	def start(self, names):
		self.game = game(self.params, self.filename, self.players_cnt, names)
		self.started = 1
		self.whose_turn = 0
		self.last_turn_time = int(time.time())
		self.all_players_cnt = len(self.players)

MAX_GAME_ID = 100000

class telegram_bot:

	def load_from_file(self):
		try:
			f = open(self.name + ".botconfig", 'r')
		except:
			return
		x = f.readlines()
		for i in range(len(x)):
			x[i] = x[i][:len(x[i]) - 1]
		self.last_update = int(x[1])
		founded_chats = json.loads(x[2])
		for chat in founded_chats:
			self.chats[chat[0]] = chat_with_bot(chat[0], self.url, self.token, "")
			self.chats[chat[0]].setparams(chat[1])
			self.all_names.add(self.chats[chat[0]].name)

	def __init__(self, _token, _name):
		self.token = _token
		self.name = _name
		self.url = "https://api.telegram.org/bot" + self.token + "/"
		self.chats = {}
		self.games = {}
		self.last_update = -1
		self.all_names = set()
		self.load_from_file()

	def get_updates(self):
		if (self.last_update == -1):
			response = requests.get(self.url + "getUpdates")
		else:
			data = {'timeout' : 5, 'offset' : self.last_update + 1}
			response = requests.get(self.url + "getUpdates", params = data)
		return response.json()['result']

	def get_new_messages(self):
		upd = self.get_updates()
		res = []
		for i in range(1, len(upd) + 1):
			if (upd[-i]['update_id'] > self.last_update):
				if ('message' in upd[-i]):
					message = upd[-i]['message']
					chat_id = message['chat']['id']
					if (chat_id >= 0):
						res.append(message)
						if (chat_id not in self.chats):
							self.chats[chat_id] = chat_with_bot(chat_id, self.url, self.token, get_name(message['from']))
			else:
				break
		if (len(upd) > 0):
			self.last_update = upd[-1]['update_id']
		return res

	def send_command(self, response_element, chat_id):
		command = response_element['command']
		response_element.pop('command')
		params = response_element
		params['chat_id'] = chat_id
		requests.post(self.url + command, data = params)

	def game_event_handler(self, game_id, event, chat_id):
		players = self.games[game_id].players
		for player_id in players:
			if (player_id == 0):
				continue
			if ('all_message' in event):
				self.send_command(markdown_message(event['all_message']), player_id)
			if (('public_message' in event) and (player_id != chat_id)):
				self.send_command(markdown_message(event['public_message']), player_id)
			if (('private_message' in event) and (player_id == chat_id)):
				self.send_command(markdown_message(event['private_message']), player_id)

	def create_game(self, player_id, is_private, params):
		print("creating game", player_id, is_private, params)
		game_id = random.randint(0, MAX_GAME_ID - 1)
		while (game_id in self.games):
			game_id = random.randint(0, MAX_GAME_ID - 1)
		self.games[game_id] = game_group(game_id, player_id, is_private, params)
		self.chats[player_id].game_id = game_id
		self.send_command(markdown_message("*ID: " + str(game_id) + "*"), player_id)

	def get_names(self, game_id):
		names = []
		for other_player_id in self.games[game_id].players:
			names.append(self.chats[other_player_id].name)
		return names

	def share_game_message(self, game_id, text):
		self.game_event_handler(game_id, {'all_message' : text}, 0)

	def player_join(self, chat_id, game_id):
		if (not(game_id in self.games)):
			self.send_command(text_message("Такой игры не существует"), chat_id)
			return
		if (self.games[game_id].started == 1):
			self.send_command(text_message("Игра уже началась"), chat_id)
			return
		self.share_game_message(game_id, self.chats[chat_id].name + " присоединился")
		names = self.get_names(game_id)
		self.chats[chat_id].game_id = game_id
		self.games[game_id].join(chat_id)
		text = "Ты в игре " + str(game_id) + " вместе с " + ", ".join(names) + ". " + description_params(self.games[game_id].params)
		self.send_command(text_message(text), chat_id)

	def player_leave(self, player_id, game_id):
		self.chats[player_id].game_id = -1
		self.games[game_id].leave(player_id)
		if (self.games[game_id].players_cnt == 0):
			self.games.pop(game_id)
			print("games.pop")
		else:
			self.share_game_message(game_id, self.chats[player_id].name + " покинул комнату")
		self.send_command(text_message("Ты покинул(а) игру"), player_id)

	def show_list(self, chat_id):
		text = ""
		index = 0
		for game_id in self.games.keys():
			if (self.games[game_id].is_private == 0):
				names = self.get_names(game_id)
				index += 1
				text = text + "Комната #" + str(index) + " (" + ", ".join(names) + "). " + description_params(self.games[game_id].params) + " /join" + str(game_id) + "\n"
		if (text == ""):
			text = "Список пуст"
		self.send_command(markdown_message(text), chat_id)

	def say(self, chat_id, game_id, message):
		text = "*" + self.chats[chat_id].name + ":* " + message
		self.share_game_message(game_id, text)

	def invite(self, chat_id, name):
		game_id = self.chats[chat_id].game_id
		if (self.games[game_id].started):
			return
		found = 0
		for player_id in self.chats.keys():
			print("id =", player_id)
			if (self.chats[player_id].name == name):
				found += 1
			self.send_command(text_message("Инвайт от " + self.chats[chat_id].name + ". /join" + str(game_id)), player_id)
		if (found == 0):
			self.send_command(text_message("Игрок не найден"), chat_id)
			return
		self.send_command(text_message("Игрок приглашён"), chat_id)

	def check_if_admin(self, chat_id, game_id):
		if (self.games[game_id].started == 1):
			self.send_command(text_message("Игра уже началась"), chat_id)
			return 0
		if (self.games[game_id].isadmin(chat_id) == 0):
			self.send_command(text_message("Чтобы изменить параметры игры, нужно быть создателем комнаты"), chat_id)
			return 0
		return 1

	def changetl(self, chat_id, game_id, tl):
		if (self.check_if_admin(chat_id, game_id)):
			self.games[game_id].tl = tl
			self.share_game_message(game_id, "Время хода изменено на " + str(tl) + " секунд")

	def load(self, chat_id):
		if (self.check_if_admin(chat_id, self.chats[chat_id].game_id)):
			self.chats[chat_id].waiting_for_file = 1
			self.send_command(text_message("Теперь отправь файл. Напиши /cancel, чтобы отменить"), chat_id)

	def remove_file(self, chat_id, game_id):
		if (self.check_if_admin(chat_id, game_id)):
			self.games[game_id].filename = ""
			self.send_command(text_message("Файл удалён"), chat_id)

	def send_turn_reminder(self, game_id):
		room = self.games[game_id]
		chat_id = room.players[room.whose_turn]
		if (chat_id != 0):
			self.send_command(text_message("Твой ход"), chat_id)

	def start_game(self, chat_id):
		game_id = self.chats[chat_id].game_id
		if (self.check_if_admin(chat_id, game_id)):
			names = []
			for player_id in self.games[game_id].players:
				names.append(self.chats[player_id].name)
			self.games[game_id].start(names)
			self.share_game_message(game_id, "Игра началась!")
			self.send_turn_reminder(game_id)

	def get_id_query(self, chat_id, player):
		if (player.game_id == -1):
			self.send_command(markdown_message("Ты не в игре"), chat_id)
		else:
			self.send_command(markdown_message("Ты в игре " + str(player.game_id)), chat_id)

	def numeric_parameter(self, chat_id, text, command, description):
		params = get_params(text, command)
		if ((len(params) == 0) or params[0].isdigit() == 0):
			self.send_command(text_message(command + " <" + description + ">"), chat_id)
			return -1
		else:
			return int(params[0])

	def game_turn(self, player_id, game_id, turn):
		room = self.games[game_id]
		player_game_id = room.players.index(player_id)
		response = room.game.turn(player_game_id, turn)
		self.game_event_handler(game_id, response, player_id)
		if (response['next_turn']):
			room.make_next_turn()
			self.send_turn_reminder(game_id)

	def handle_message(self, message):
		print("GOT MESSAGE")
		chat_id = message['chat']['id']
		player = self.chats[chat_id]

		if (('document' in message) and player.waiting_for_file == 1):
			file_id = message['document']['file_id']
			_params = {'file_id' : file_id}
			response = requests.get(self.url + "getFile", params = _params).json()
			file_path = response['result']['file_path']
			download_url = "https://api.telegram.org/file/bot" + self.token + "/" + file_path
			os.system("wget -O map" + str(player.game_id) + " " + download_url)
			player.waiting_for_file = 0
			self.games[player.game_id].filename = "map" + str(player.game_id)
			self.send_command(markdown_message("Файл загружен"), chat_id)
			return

		player.waiting_for_file = 0

		if ('text' in message):
			text = message['text']
			command = get_command(text)

			print("text", text)
			print("command", command)

			if (command == '/start'):
				self.send_command(markdown_message(INTRO), chat_id)
			if (command == '/rules'):
				self.send_command(markdown_message(RULES), chat_id)
			if (command == '/help'):
				self.send_command(markdown_message(HELP_MESSAGE), chat_id)
			if (command == '/getname'):
				self.send_command(markdown_message("Тебя зовут _" + self.name + "_"))
			if (command == '/list'):
				self.show_list(chat_id)
			if (command == '/getid'):
				self.get_id_query(chat_id, player)

			if (player.game_id == -1):
				if (command == '/setname'):
					params = get_params(text, "/setname")
					if (len(params) == 0):
						self.send_command(text_message("/setname <name>"), chat_id)
					name = ' '.join(params)
					if (not correct(name)):
						self.send_command(text_message(WRONG_CHARECTERS_IN_NAME_MESSAGE), chat_id)
					if (name in all_names):
						self.send_command(text_message("Это имя занято"), chat_id)
					all_names.remove(player.name)
					player.name = name
					all_names.add(player.name)
					self.send_command(markdown_message("Теперь ты _" + name + "_"), chat_id)

				if (command == '/create_game'):
					params = get_params(text, '/create_game')
					self.create_game(chat_id, 0, params)

				if (command == '/create_private_game'):
					params = get_params(text, '/create_private_game')
					self.create_game(chat_id, 1, params)

				if (command == '/join'):
					game_id = self.numeric_parameter(chat_id, text, '/join', 'GAME_ID')
					if (game_id != -1):
						self.player_join(chat_id, game_id)
			else:
				room = self.games[player.game_id]

				if (command == '/say'):
					to_say = suffix(text, '/say')
					self.say(chat_id, player.game_id, to_say)

				if (command == '/leave'):
					self.player_leave(chat_id, player.game_id)
					return

				if (command == '/join'):
					self.send_command(text_message("Сначала выйди из этой игры (/leave)"), chat_id)

				if (room.started == 0):
					if (command == '/invite'):
						invited = suffix(text, '/invite')
						self.invite(chat_id, invited)

					if (command == '/changetl'):
						tl = self.numeric_parameter(chat_id, text, '/changetl', 'TL')
						if (tl != -1):
							self.changetl(chat_id, player.game_id, tl)

					if (command == '/load'):
						self.load(chat_id)

					if (command == '/remove_file'):
						self.remove_file(chat_id)

					if (command == '/start_game'):
						self.start_game(chat_id)
				else:
					self.game_turn(chat_id, player.game_id, text)
		else:
			self.send_command(text_message(WRONG_MESSAGE_RESPONSE), chat_id)

	def update_game(self, game_id):
		room = self.games[game_id]
		while (room.players[room.whose_turn] == 0):
			response = room.game.random_turn(self.whose_turn)
			self.game_event_handler(game_id, response, 0)
			room.make_next_turn()
			self.send_turn_reminder(game_id)

		if (time.time() - room.last_turn_time >= room.tl):
			afk_player_id = room.players[room.whose_turn]
			afk_player_name = self.chats[afk_player_id].name
			self.chats[afk_player_id].game_id = -1
			room.players[room.whose_turn] = 0
			room.players_cnt -= 1
			self.send_command(text_message("Время хода истекло"), afk_player_id)
			self.share_game_message(game_id, 'Игрок _' + afk_player_name + '_ афк')
			if (room.players_cnt == 0):
				self.games.pop(game_id)

	def update(self):
		print("updating bot...", int(time.time()))
		messages = self.get_new_messages()[::-1]
		for msg in messages:
			self.handle_message(msg)

		game_keys = list(self.games.keys())
		for game_id in game_keys:
			if (self.games[game_id].started == 1):
				self.update_game(game_id)

	def save_to_file(self):
		f = open(self.name + ".botconfig", 'w')
		f.write("Configuration to bot " + self.name + "\n")
		f.write(str(self.last_update) + "\n")
		stringchats = '['
		it = []
		for x in self.chats.items():
			it.append(x)
		for i in range(len(it)):
			x = it[i]
			stringchats = stringchats + '[' + str(x[0]) + ', "' + str(x[1]) + '"]'
			if (i < len(it) - 1):
				stringchats += ', '
		stringchats += ']'
		f.write(stringchats + "\n")

bot = telegram_bot(TOKEN, BOT_NAME)

def exit_handler():
	bot.save_to_file()

atexit.register(exit_handler)

while (True):
	try:
		bot.update()
		bot.save_to_file()
	except KeyboardInterrupt:
		break