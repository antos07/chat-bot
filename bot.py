from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import config
import psycopg2 as ps2
from random import randint

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
			cur.execute("SELECT cur_topic_id, cur_question_id FROM users WHERE user_id = %s", (chat.id,))
			topic_id, question_id = cur.fetchone()
			log('recieved topic_id = {topic}, question_id = {question}'.format(topic = topic_id, question = question_id))
			if topic_id is None:
				log('updating topic')
				cur.execute("SELECT id from topics WHERE topic = %s", (upd.message.text,))
				if cur.rowcount == 0:
					chat.send_message("Вы должны выбрать тему")
				else:
					topic_id = cur.fetchone()[0]
					cur.execute("UPDATE users SET cur_topic_id = %s WHERE user_id = %s", (topic_id, chat.id))
					conn.commit()
					log('topic_id =', topic_id)
					ask_question(chat)
			else:
				msg = upd.message.text
				if msg == 'Выбрать тему':
					choose_topic(chat)
				else:
					log("checking answer for user", chat.id)
					cur.execute("SELECT answer FROM questions WHERE id = %s", (question_id,))
					answer = cur.fetchone()[0]
					
					cur.execute("UPDATE stats SET total = total + 1 WHERE user_id = %s AND topic_id = %s",
							(chat.id, topic_id))
					conn.commit()
					log("{} rows were affected".format(cur.rowcount))
					if cur.rowcount == 0:
						cur.execute("INSERT INTO stats VALUES (%s, %s, 0, 1)", (chat.id, topic_id))
					log("total questions in topic {} was updated for user {}".format(topic_id, chat.id))
					if msg == answer:
						chat.send_message("Правильный ответ")
						cur.execute("UPDATE stats SET correct = correct + 1 WHERE user_id = %s AND topic_id = %s",
								(chat.id, topic_id))
					else:
						chat.send_message("Неправильноый ответ")
						chat.send_message('Правильный ответ был "{}"'.format(answer))

					ask_question(chat)

	except Exception as e:
		log('error', e)


def ask_question(chat):
	log('making question for user', chat.id)
	with conn.cursor() as cur:
		cur.execute("SELECT id, question, variants FROM questions WHERE topic_id IN (SELECT cur_topic_id FROM users WHERE user_id = %s)", (chat.id,))
		question_number = randint(1, cur.rowcount)
		log('question_number is', question_number)
		for i in range(question_number - 1):
			cur.fetchone()
		question_id, question, variants = cur.fetchone()
		log("question is:", question, "\n", "variants are:", variants)
		cur.execute("UPDATE users SET cur_question_id = %s WHERE user_id = %s", (question_id, chat.id))
		conn.commit()
		log('cur_question_id was updated for user', chat.id)
		keyboard = [[variant for variant in variants], ['Выбрать тему']]
		tg_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard = True, one_time_keyboard = True)
		chat.send_message(question, reply_markup = tg_keyboard)
		log('question was sent to user', chat.id)


dp.add_handler(MessageHandler(Filters.text, recieved_msg))


def stats(bot, upd):
	chat = upd.effective_chat
	log("asked for stats in chat", chat.id)
	stats_template = 'По теме "{topic}" у вас {correct} правильных ответов из {total}\n'
	answer = "Вашы статистика правильных ответов:\n"

	with conn.cursor() as cur:
		cur.execute("SELECT topic_id, correct, total FROM stats WHERE user_id = %s", (chat.id,))
		stats = cur.fetchall()

		for i in stats:
			cur.execute('SELECT topic from topics WHERE id = %s', (i[0],))
			topic = cur.fetchone()[0]
			answer += stats_template.format(topic = topic, correct = i[1], total = i[2])

	log("answer for chat {} is".format(chat.id), answer)
	chat.send_message(answer)
	log("answered in chat", chat.id)


dp.add_handler(CommandHandler('stats', stats))


def clear():
	with conn.cursor() as cur:
		cur.execute("DELETE FROM users")
		conn.commit()
		cur.execute("DELETE FROM stats")
		conn.commit()
		log("cleared")

updater.start_polling()
updater.idle()
if config.DEBUG:
	clear()
conn.close()
log('stopped')