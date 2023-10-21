import os
import pandas as pd
import sqlite3 as sl
from typing import Union


class CrawlDatabase:
  """Python abstraction for an SQLite database. Built specifically for Atlas-Crawl

  Can run queries to populate the database with crawl data or can request data with
  pre-determined queries. Exposes the dataset cursor for custom queries.

  Parameters
  ----------
  db_path: Union[str, os.PathLike]
    Path to the database file.

  Examples
  --------
  >>> from database import CrawlDatabase
  >>> schema = open("/path/to/schema.sql", "r").read()
  >>> db = CrawlDatabase.create_from_schema(schema, "/path/to/save/database/db")
  >>> top_hs = db.get_top_highschools(year=2022) # Pre-determined query example
  >>> results = db.query("some_sql_query") # Custom query example.
  >>> db.close()
  """

  def __init__(self, db_path: Union[str, os.PathLike]):
    self.path = db_path
    if os.path.exists(self.path):
      self.conn = sl.connect(self.path)
    else:
      raise ValueError(f"Pointed database file {self.path} does not exists!")

  @classmethod
  def create_from_schema(cls, schema: str, path: Union[str, os.PathLike]):
    """ Create database that supports foreign keys from a schema.
    
    Parameters
    -----------
    schema: str 
      SQL schema to define the database structure.
    path: Union[str, os.PathLike]
      Path to save the database.

    Returns
    ---------
    db: CrawlDatabase
      Handle for the created database.
    """

    if os.path.exists(path):
      print(f"!ERROR: {db_path} exists!")
      choice = input(
          f"Do you want to override the record on {db_path}? [y/n]: ")
      if 'y' in choice.lower():
        os.remove(db_path)
      else:
        print("Abort.")
        return None

    conn = sl.connect(path)
    curr = conn.cursor()

    # This is done to enable foreign keys which are required to connect tables
    # together by refering one table from another table using the key from the
    # original table
    query = """PRAGMA foreign_keys = 1;"""
    curr.execute(query)
    curr.executescript(schema)
    conn.commit()

    conn.close()
    print("Database is successfully created!")
    return cls(path)

  def close(self):
    """ Close the connection to database gracefully """
    self.conn.close()


if __name__ == "__main__":
  with open("../data/schema.sql", "r") as f:
    schema = f.read()
  db = CrawlDatabase.create_from_schema(schema, "../data/crawl_database.db")
