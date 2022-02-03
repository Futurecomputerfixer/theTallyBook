import sqlite3

def connect():
    conn = sqlite3.connect('theTallyBookdb.sqlite')
    sqlstr = '''
CREATE TABLE IF NOT EXISTS entry( 
	description TEXT,
	amount INTEGER,
	category_id INTEGER,
	user_id INTEGER,
	entry_date TEXT,
	FOREIGN KEY(user_id)
		REFERENCES "user"(id),
	FOREIGN KEY(category_id)
		REFERENCES category(id)
);
CREATE TABLE IF NOT EXISTS category (
	id INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT,
	category TEXT,
	user_id INTEGER,
	FOREIGN KEY(user_id)
		REFERENCES user(id)
);
CREATE TABLE IF NOT EXISTS user (
	id INTEGER NOT NULL  PRIMARY KEY AUTOINCREMENT ,
	username TEXT,
	hash TEXT
)'''
    conn.executescript(sqlstr)
    return conn