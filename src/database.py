import os
import time
import logging
import pandas as pd
import sqlite3 as sl
from typing import Union, Dict, Any

# Set up logging
db_logger = logging.getLogger("db_logger")
db_logger.setLevel(logging.INFO)
db_handler = logging.FileHandler("../logs/db_operations.log")
db_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
db_handler.setFormatter(db_formatter)
db_logger.addHandler(db_handler)


class CrawlDatabase:
  """
  Python abstraction for an SQLite database. Built specifically for Atlas-Crawl

  Can run queries to populate the database with crawl data or can request data with
  pre-determined queries. Exposes the dataset cursor for custom queries.

  Parameters
  ----------
  db_path
    Path to the database file.

  Raises
  ------
  FileNotFoundError
    If the pointed database path does not exists, raises this error
  """
  def __init__(self, db_path: Union[str, os.PathLike]):
    self.path = db_path
    if self.path == ":memory:" or os.path.exists(self.path):
      self.conn = sl.connect(self.path, check_same_thread=False)
    else:
      raise FileNotFoundError(f"Pointed database file {self.path} does not exists!")

  @classmethod
  def create_from_schema(cls, *, schema: str, path: Union[str, os.PathLike]):
    """
    Create database that supports foreign keys from a schema.

    Parameters
    -----------
    schema
      SQL schema to define the database structure.
    path
      Path to save the database.

    Returns
    ---------
    db
      Handle for the created database.

    Raises
    ------
    FileExistsError
      If the supplied path already exists this error is raised
    """

    if os.path.exists(path):
      raise FileExistsError(f"{path} already exists!")
    conn = sl.connect(path)
    curr = conn.cursor()

    # This is done to enable foreign keys which are required to connect tables
    # together by refering one table from another table using the key from the
    # original table
    curr.execute("""PRAGMA foreign_keys = ON;""")
    curr.executescript(schema)
    conn.commit()
    conn.close()

    print("Database is successfully created!")
    return cls(path)

  def query(self, query_str: str, query_args: tuple = ()):
    """ Exposed API for running custom queries. Mostly used for testing """
    if "select" in query_str.lower():
      results = pd.read_sql(query_str, self.conn, params=query_args)
      return results
    else:
      cursor = self.conn.cursor()
      cursor.execute(query_str, query_args)
      self.conn.commit()

  def thread_safe_write(self, query: str, *args) -> bool:
    cursor = self.conn.cursor()
    attempts = 0
    while attempts < 5:
      try:
        cursor.execute(query, *args)
        self.conn.commit()
        return True
      except sl.Error as e:
        if "UNIQUE" in str(e):
          return True
        else:
          db_logger.error(
            f"Write error: {e} for query {query} with arguments {args}, retrying in 0.05 seconds"
          )
          time.sleep(0.05)
          attempts += 1
    db_logger.error(f"Failed to write data {args} after 5 attempts")
    return False

  def write_university(self, uni_name: str, uni_type: str, uni_city: str, **kwargs) -> bool:
    query = """
    INSERT INTO
      University (UniversityName, UniversityType, UniversityCity)
    VALUES
      (?, ?, ?)
    """
    return self.thread_safe_write(query, (uni_name, uni_type, uni_city))

  def write_faculty(self, uni_name: str, fac_name: str, **kwargs) -> bool:
    query = """
    INSERT INTO
      Faculty (UniversityID, FacultyName)
    SELECT
      u.UniversityID,
      :fac_name
    FROM
      University u
    WHERE
      u.UniversityName = :uni_name;
    """
    return self.thread_safe_write(query, {"uni_name": uni_name, "fac_name": fac_name})

  def write_program(
    self, dept_id: int, dept_name: str, dept_type: str, scholarship: str, uni_name: str,
    fac_name: str, **kwargs
  ) -> bool:
    query = """
    INSERT INTO
      Program (ProgramID, ProgramName, ProgramType, ScholarshipType, FacultyID)
    SELECT
      :prog_id,
      :prog_name,
      :prog_type,
      :scholarship,
      f.FacultyID
    FROM
      University u
      JOIN Faculty f ON u.UniversityID = f.UniversityID
    WHERE
      u.UniversityName = :uni_name
      AND f.FacultyName = :fac_name
    """
    return self.thread_safe_write(
      query, {
        "prog_id": dept_id,
        "prog_name": dept_name,
        "prog_type": dept_type,
        "scholarship": scholarship,
        "uni_name": uni_name,
        "fac_name": fac_name,
      }
    )

  def write_placement(
    self, dept_id: int, total_quota: int, total_placed: Union[int, None],
    min_points: Union[float, None], max_points: Union[float, None], min_ranking: Union[int, None],
    max_ranking: Union[int, None], year: int, **kwargs
  ) -> bool:
    query = """
    INSERT INTO
      PlacementData (ProgramID, TotalQuota, TotalPlaced, LowestScore, HighestScore, MinimumRanking, MaximumRanking, Year)
    VALUES (
      :prog_id,
      :total_quota,
      :total_placed,
      :min_points,
      :max_points,
      :min_ranking,
      :max_ranking,
      :year
    );
    """
    return self.thread_safe_write(
      query, {
        "prog_id": dept_id,
        "total_quota": total_quota,
        "total_placed": total_placed,
        "min_points": min_points,
        "max_points": max_points,
        "min_ranking": min_ranking,
        "max_ranking": max_ranking,
        "year": year,
      }
    )

  def write_highschools(self, df: pd.DataFrame) -> bool:
    query = """
    INSERT INTO
      HighSchool (HighSchoolName, City, District, CounselorName, CounselorPhone, CounselorEmail)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    results = []
    for x in df[["hs", "hs_city", "hs_district"]].itertuples():
      results.append(
        self.thread_safe_write(query, (x.hs, x.hs_city, x.hs_district, None, None, None))
      )
    return all(results)

  def write_highschool_placements(self, df: pd.DataFrame, program_id: int, year: int) -> bool:
    query = """
    INSERT INTO
      HighSchoolPlacement (HighSchoolID, ProgramID, Year, NumberOfNewGrads, NumberOfOldGrads)
    SELECT
      h.rowid,
      :prog_id,
      :year,
      :new_grads,
      :old_grads
    FROM
      HighSchool h
    WHERE
      h.HighSchoolName = :hs_name AND h.City = :hs_city AND h.District = :hs_district
    """
    results = []
    for x in df[["hs", "hs_city", "hs_district", "new_grad", "old_grad"]].itertuples():
      arg = {
        "prog_id": program_id,
        "year": year,
        "new_grads": int(x.new_grad),
        "old_grads": int(x.old_grad),
        "hs_name": x.hs,
        "hs_city": x.hs_city,
        "hs_district": x.hs_district
      }
      results.append(self.thread_safe_write(query, arg))
    return all(results)

  def __del__(self):
    """ Close the connection to database gracefully """
    self.conn.close()


if __name__ == "__main__":
  with open("./schema.sql", "r", encoding="utf-8") as f:
    schema = f.read()
  try:
    db = CrawlDatabase.create_from_schema(schema=schema, path="../data/crawl_database.db")
  except FileExistsError as e:
    print(e)
