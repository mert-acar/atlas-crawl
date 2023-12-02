import os
import pandas as pd
import sqlite3 as sl
from typing import Union, Dict, Any


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
      raise FileNotFoundError(
          f"Pointed database file {self.path} does not exists!"
      )

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

  def write_rankings(self, data: Dict[str, Any]):
    cursor = self.conn.cursor()
    query = """
    INSERT OR IGNORE INTO
      University (UniversityName, UniversityType, UniversityCity)
    VALUES
      (?, ?, ?)
    """
    cursor.execute(
        query, (data["uni_name"], data["uni_type"], data["uni_city"])
    )

    query = """
    INSERT OR IGNORE INTO
      Faculty (UniversityID, FacultyName)
    SELECT
      u.rowid,
      :fac_name
    FROM
      University u
    WHERE
      u.UniversityName = :uni_name;
    """
    cursor.execute(
        query, {
            "uni_name": data["uni_name"],
            "fac_name": data["fac_name"]
        }
    )

    query = """
    INSERT OR IGNORE INTO
      Program (ProgramID, ProgramName, ProgramType, ScholarshipType, FacultyID)
    SELECT
      :prog_id,
      :prog_name,
      :prog_type,
      :scholarship,
      f.rowid
    FROM
      University u
      JOIN Faculty f ON u.rowid = f.UniversityID
    WHERE
      u.UniversityName = :uni_name
      AND f.FacultyName = :fac_name
    """
    cursor.execute(
        query, {
            "prog_id": data["dept_id"],
            "prog_name": data["dept_name"],
            "prog_type": data["dept_type"],
            "scholarship": data["scholarship"],
            "uni_name": data["uni_name"],
            "fac_name": data["fac_name"],
        }
    )

    query = """
    INSERT OR IGNORE INTO
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
    cursor.execute(
        query, {
            "prog_id": data["dept_id"],
            "total_quota": data["total_quota"],
            "total_placed": data["total_placed"],
            "min_points": data["min_points"],
            "max_points": data["max_points"],
            "min_ranking": data["min_ranking"],
            "max_ranking": data["max_ranking"],
            "year": data["year"],
        }
    )
    self.conn.commit()

  def write_highschools(self, df: pd.DataFrame, program_id: int, year: int):
    cursor = self.conn.cursor()
    query = """
    INSERT OR IGNORE INTO
      HighSchool (HighSchoolName, City, District, CounselorName, CounselorPhone, CounselorEmail)
    VALUES (?, ?, ?, NULL, NULL, NULL)
    """
    cursor.executemany(
        query, [
            (x.hs, x.hs_city, x.hs_district)
            for x in df[["hs", "hs_city", "hs_district"]].itertuples()
        ]
    )

    query = """
    INSERT OR IGNORE INTO
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
    cursor.executemany(
        query, [
            {
                "prog_id": program_id,
                "year": year,
                "new_grads": int(x.new_grad),
                "old_grads": int(x.old_grad),
                "hs_name": x.hs,
                "hs_city": x.hs_city,
                "hs_district": x.hs_district
            } for x in df[[
                "hs", "hs_city", "hs_district", "new_grad", "old_grad"
            ]].itertuples()
        ]
    )
    self.conn.commit()

  def close(self):
    """ Close the connection to database gracefully """
    self.conn.close()


if __name__ == "__main__":
  with open("./schema.sql", "r") as f:
    schema = f.read()

  try:
    db = CrawlDatabase.create_from_schema(
        schema=schema, path="../data/crawl_database.db"
    )
  except FileExistsError as e:
    print(e)
