import os
import sqlite3
from functools import lru_cache
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple


class AtlasDBManager:
  def __init__(self, db_path: str):
    self.db_path = db_path
    self._connection = None

  @classmethod
  def create_from_schema(cls, *, schema_path: str, database_path: str):
    if os.path.exists(database_path):
      raise FileExistsError(f"{database_path} already exists!")

    with sqlite3.connect(database_path) as conn:
      with open(schema_path, 'r', encoding='utf-8') as schema_file:
        conn.executescript(schema_file.read())
      conn.commit()
    print(f"Database is successfully created: {database_path}!")
    return cls(database_path)

  @contextmanager
  def get_connection(self):
    """Context manager for database connections."""
    if self._connection is None:
      self._connection = sqlite3.connect(self.db_path)
      self._connection.row_factory = sqlite3.Row

    try:
      yield self._connection
    except Exception as e:
      self._connection.rollback()
      raise e

  def close(self) -> None:
    """Close the database connection."""
    if self._connection:
      self._connection.close()
      self._connection = None

  def execute_many(self, query: str, parameters: List[Tuple]) -> None:
    """
    Execute multiple insertions or updates.
    
    Args:
        query: SQL query with placeholders
        parameters: List of parameter tuples
    """
    with self.get_connection() as conn:
      conn.executemany(query, parameters)
      conn.commit()

  @lru_cache(maxsize=128)
  def cached_query(self, query: str, parameters: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query with caching.
    
    Args:
        query: SQL query
        parameters: Query parameters (must be hashable for caching)
        
    Returns:
        List of dictionaries containing the query results
    """
    with self.get_connection() as conn:
      cursor = conn.execute(query, parameters or ())
      columns = [col[0] for col in cursor.description]
      return [dict(zip(columns, row)) for row in cursor.fetchall()]

  def clear_cache(self) -> None:
    """Clear the query cache."""
    self.cached_query.cache_clear()

  # University-related methods
  def add_university(self, name: str, type_: str, city: str) -> Optional[int]:
    """Add a new university and return its ID."""
    with self.get_connection() as conn:
      cursor = conn.execute(
        "INSERT INTO University (UniversityName, UniversityType, UniversityCity) VALUES (?, ?, ?)",
        (name, type_, city)
      )
      conn.commit()
      return cursor.lastrowid

  def add_faculty(self, university_id: int, name: str) -> Optional[int]:
    """Add a new faculty and return its ID."""
    with self.get_connection() as conn:
      cursor = conn.execute(
        "INSERT INTO Faculty (UniversityID, FacultyName) VALUES (?, ?)", (university_id, name)
      )
      conn.commit()
      return cursor.lastrowid

  def add_program(self, faculty_id: int, name: str, scholarship_type: str,
                  program_type: str) -> Optional[int]:
    """Add a new program and return its ID."""
    with self.get_connection() as conn:
      cursor = conn.execute(
        """INSERT INTO Program 
                   (FacultyID, ProgramName, ScholarshipType, ProgramType) 
                   VALUES (?, ?, ?, ?)""", (faculty_id, name, scholarship_type, program_type)
      )
      conn.commit()
      return cursor.lastrowid

  def add_placement_data(
    self, program_id: int, year: int, lowest_score: float, highest_score: float, total_quota: int,
    total_placed: int, max_ranking: int, min_ranking: int
  ) -> None:
    """Add placement data for a program."""
    with self.get_connection() as conn:
      conn.execute(
        """INSERT INTO PlacementData 
                   (ProgramID, Year, LowestScore, HighestScore, TotalQuota, 
                    TotalPlaced, MaximumRanking, MinimumRanking)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
          program_id, year, lowest_score, highest_score, total_quota, total_placed, max_ranking,
          min_ranking
        )
      )
      conn.commit()

  def add_high_school(
    self,
    name: str,
    city: str,
    district: str,
    score: float = None,
    counselor_name: str = None,
    counselor_phone: str = None,
    counselor_email: str = None
  ) -> Optional[int]:
    """Add a new high school and return its ID."""
    with self.get_connection() as conn:
      cursor = conn.execute(
        """INSERT INTO HighSchool 
                   (HighSchoolName, City, District, Score, 
                    CounselorName, CounselorPhone, CounselorEmail)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, city, district, score, counselor_name, counselor_phone, counselor_email)
      )
      conn.commit()
      return cursor.lastrowid

  def add_high_school_placement(
    self, high_school_id: int, program_id: int, year: int, new_grads: int, old_grads: int
  ) -> None:
    """Add high school placement data."""
    with self.get_connection() as conn:
      conn.execute(
        """INSERT INTO HighSchoolPlacement 
                   (HighSchoolID, ProgramID, Year, NumberOfNewGrads, NumberOfOldGrads)
                   VALUES (?, ?, ?, ?, ?)""",
        (high_school_id, program_id, year, new_grads, old_grads)
      )
      conn.commit()

  def placement_data_exists(self, program_id: int, year: int) -> bool:
    """
    Check if placement data exists for a specific program and year.
    
    Args:
        program_id: ID of the program to check
        year: Year of the placement data
        
    Returns:
        bool: True if data exists, False otherwise
    """
    with self.get_connection() as conn:
      cursor = conn.execute(
        """SELECT 1 FROM PlacementData 
                   WHERE ProgramID = ? AND Year = ? 
                   LIMIT 1""",
        (program_id, year)
      )
      return cursor.fetchone() is not None


if __name__ == "__main__":
  try:
    db = AtlasDBManager.create_from_schema(schema_path="./schema.sql", database_path="../test.db")
  except FileExistsError as e:
    print(e)
