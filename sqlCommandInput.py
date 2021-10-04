import os
from sqlalchemy import create_engine

DATABASE_URL = os.environ['DATABASE_URL']

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


d = create_engine(DATABASE_URL, echo = False)

qry=str(input('enter your sql commands\n'))
print(qry)
ss=d.execute(qry)
print(ss,ss.fetchall())

#python3 sqlCommandInput.py
