"""Minimal Postgres adapter for existing fixed SQL, not an arbitrary-query gateway."""
import os
import psycopg
from psycopg.rows import dict_row
class DB:
 def __init__(self):self.c=psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row)
 def execute(self,sql,args=()):
  if sql=='BEGIN IMMEDIATE':sql='BEGIN'
  return self.c.execute(sql.replace('?','%s'),args)
 def __enter__(self):return self
 def __exit__(self,t,v,tb):
  try:self.c.rollback() if t else self.c.commit()
  finally:self.c.close()
def install(core):
 def init(_):
  with DB() as c:
   c.execute('CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, query_id TEXT UNIQUE NOT NULL, spec TEXT NOT NULL, report TEXT NOT NULL, artifact_hash TEXT NOT NULL, status TEXT NOT NULL, mode TEXT NOT NULL, order_id TEXT, capture_id TEXT, created BIGINT NOT NULL)')
   c.execute('CREATE TABLE IF NOT EXISTS events(id BIGSERIAL PRIMARY KEY, report_id TEXT, action TEXT NOT NULL, detail TEXT NOT NULL, created BIGINT NOT NULL)')
 core.init=init;core.connect=lambda _:DB()
