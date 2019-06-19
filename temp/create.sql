create table users(
	user_id integer primary key,
	cur_topic_id integer,
	cur_question_id integer
);

create table topics(
	id serial primary key,
	topic varchar(100)
);

create table questions(
	id serial primary key,
	topic_id integer,
	question text,
	variants varchar(100)[],
	answer varchar(100)
);
	
create table stats(
	user_id integer,
	topic_id integer,
	correct integer,
	total integer
)