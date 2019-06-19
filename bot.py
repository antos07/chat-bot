from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import config
import psycopg2 as ps2

updater = Updater(config.TOKEN)
dp = updater.dispatcher

conn = ps2.connect(config.DATABASE_URL)


def log(*data):
	print('[log]', *data)


def error(bot, upd, e):
	log('error in update', upd.update_id, '-', e)


dp.add_error_handler(error)
log('inited')


def choose_topic(chat):
	log('choosing topic in chat {chat_id}'.format(chat_id = chat.id))
	with conn.cursor() as cur:

		cur.execute("UPDATE users SET cur_topic_id = null, cur_question_id = null WHERE user_id=%s", (chat.id,))
		conn.commit()
		log('{user_id} topic was annulled'.format(user_id = chat.id))

		cur.execute("SELECT topic FROM topics")
		topics = cur.fetchall()
		log('get topics: ' +  str(topics))
		keyboard = [[topic[0] for topic in topics]]
		tg_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard = True)
		chat.send_message('Выберите тему', reply_markup = tg_keyboard)
		log('topics were sent')


def start(bot, upd):
	chat = upd.effective_chat
	log('start from chat {chat_id}'.format(chat_id = chat.id))

	if chat.type != chat.PRIVATE:
		chat.send_message("Я работаю только в личных сообщениях")
		return

	with conn.cursor() as cur:
		cur.execute("SELECT user_id FROM users WHERE user_id=%s", (chat.id,))
		if cur.rowcount != 0:
			chat.send_message("Тестирование уже начато")
		else:
			cur.execute("INSERT INTO users (user_id) VALUES (%s)", (chat.id, ))
			conn.commit()
			chat.send_message("Вы успешно начали Тестирование")
			choose_topic(chat)


dp.add_handler(CommandHandler("start", start))


def recieved_msg(bot, upd):
	chat = upd.effective_chat
	log('msg from chat', chat.id)

	try:
		with conn.cursor() as cur:
			cur.execute("SELECT cur_topic_id, cur_question_id FROm users WHERE user_id = %s", (chat.id,))
			topic_id, question_id = cur.fetchone()
			log('recieved topic_id = {topic}, question_id = {question}'.format(topic = topic_id, question = question_id))
			if topic_id is None:
				log('updating topic')
				cur.execute("SELECT id from topics WHERE topic = %s", (upd.message.text,))
				if cur.rowcount == 0:
					chat.send_message("Вы должны выбрать тему")
				else:
					topic_id = cur.fetchone()[0]
					cur.execute("UPDATE users SET cur_topic_id = %s", (topic_id, ))
					conn.commit()
					log('topic_id =', topic_id)
					ask_question(chat)
	except Exception as e:
		log('error', e)


def ask_question(chat):
	pass


dp.add_handler(MessageHandler(Filters.text, recieved_msg))

updater.start_polling()
updater.idle()
conn.close()
log('stopped')