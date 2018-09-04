#   RULES - правила игры, INTRO - краткое описание, DEFALUT_TL - стандартное время на ход (в секундах)
RULES = "Правила"
INTRO = "Интро"
DEFALUT_TL = 180

class game:

	#   инициализация, params - массив строк (параметры игры), filename - путь до файла с картой, players_cnt - количество игорков, player_names - массив их хэндлов
	def __init__(self, params, filename, players_cnt, player_names):
		pass

	#   игрок с номером player_id делает ход turn
	#   возвращает словарь, 'next_turn' - верно ли, что сменился ход, 'all_message' - сообщение всем, 'private_message' - сообщение этому игроку, 'public_message' - сообщение остальным
	def turn(self, player_id, turn):
		return {'next_turn' : 1, 'all_message' : 'Игрок ' + str(player_id) + ' сходил'}

	#   то же, но за игрока player_id должен сходить бот, 'next_turn' = 1.
	def random_turn(self, player_id):
		return {'all_message' : 'Бот ' + str(player_id) + ' сходил'}

#   возвращает описание специфики правил по параметрам
def description_params(params):
	return "Правила дефолтные."