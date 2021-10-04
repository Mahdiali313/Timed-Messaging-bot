#run this code with command to init sql table
import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()


try:
    cur.execute('''CREATE TABLE messagelists
       (num   SERIAL,
        time   TEXT,
	    message	TEXT,
        userid   TEXT,
        token   TEXT
        );''')
        
    conn.commit()
except:
    print("faile to make messagelists table")
	

try:
    cur.execute('''CREATE TABLE userdata
       (chatid  INT ,
	    status  TEXT,
	    timesendpost  TEXT,
	    channelid   TEXT,
        token   TEXT,
        idselected  TEXT
        );''')
    
    conn.commit()

except:
    print("faile to make userData table")

conn.close()