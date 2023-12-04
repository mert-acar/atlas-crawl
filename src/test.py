""" Test script for database validation during schema development """

from database import CrawlDatabase
from sqlite3 import Error, IntegrityError


def test_unique_constraint(db: CrawlDatabase) -> bool:
  """ Test the unique constraint on the UniversityName field in the University table """
  passed = False
  try:
    # Creating a temporary University table to test
    create_table_sql = """
    CREATE TEMP TABLE IF NOT EXISTS University_Test (
      UniversityID INTEGER PRIMARY KEY,
      UniversityName TEXT NOT NULL UNIQUE,
      UniversityType TEXT CHECK(UniversityType IN ('Private', 'State')),
      UniversityCity TEXT NOT NULL
    );
    """
    db.query(create_table_sql)

    # Inserting a university record
    insert_sql = "INSERT INTO University_Test (UniversityName, UniversityType, UniversityCity) VALUES (?, ?, ?);"
    db.query(insert_sql, ("Test University", "Private", "Test City"))

    # Trying to insert another university with the same name
    try:
      # If this succeeds, the test fails
      db.query(insert_sql, ("Test University", "State", "Another City"))
    except IntegrityError:
      passed = True  # Expected behavior, the test passes

  except Error as e:
    print(e)
  finally:
    # Cleaning up by dropping the temp table
    db.query("DROP TABLE IF EXISTS University_Test")
  return passed


def test_referential_integrity(db: CrawlDatabase) -> bool:
  """ Test the referential integrity between Faculty and University tables with foreign key enforcement """
  passed = False
  try:
    db.query("PRAGMA foreign_keys = ON;")

    # Rest of the test is the same as before
    # Creating temporary tables
    create_university_sql = """
    CREATE TEMP TABLE IF NOT EXISTS University_Test (
        UniversityID INTEGER PRIMARY KEY,
        UniversityName TEXT NOT NULL UNIQUE,
        UniversityType TEXT CHECK(UniversityType IN ('Private', 'State')),
        UniversityCity TEXT NOT NULL
    );
    """
    db.query(create_university_sql)

    create_faculty_sql = """
    CREATE TEMP TABLE IF NOT EXISTS Faculty_Test (
        FacultyID INTEGER PRIMARY KEY,
        UniversityID INTEGER NOT NULL,
        FacultyName TEXT NOT NULL,
        UNIQUE (UniversityID, FacultyName),
        FOREIGN KEY (UniversityID) REFERENCES University_Test(UniversityID)
    );
    """
    db.query(create_faculty_sql)

    # Inserting a record into the University table
    db.query(
      "INSERT INTO University_Test (UniversityName, UniversityType, UniversityCity) VALUES (?, ?, ?);",
      ("Test University", "Private", "Test City")
    )

    # Inserting a valid record into the Faculty table
    db.query(
      "INSERT INTO Faculty_Test (UniversityID, FacultyName) VALUES (?, ?);", (1, "Test Faculty")
    )

    # Attempting to insert a record with an invalid UniversityID into the Faculty table
    try:
      # If this succeeds, the test fails
      db.query(
        "INSERT INTO Faculty_Test (UniversityID, FacultyName) VALUES (?, ?);",
        (999, "Invalid Faculty")
      )
    except IntegrityError:
      passed = True  # Expected behavior, the test passes

  except Error as e:
    print(e)
  finally:
    # Cleaning up by dropping the temp tables
    db.query("DROP TABLE IF EXISTS Faculty_Test")
    db.query("DROP TABLE IF EXISTS University_Test")
  return passed


def check_foreign_keys(db: CrawlDatabase):
  """
  Function to check the integrity of foreign keys in an SQLite database.

  Args:
  db: Database object handle
  """

  cursor = db.conn.cursor()
  # SQL query to get the list of tables with foreign keys
  cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
  tables = [table[0] for table in cursor.fetchall()]

  for table in tables:
    # Get foreign key details for each table
    cursor.execute(f"PRAGMA foreign_key_list({table});")
    foreign_keys = cursor.fetchall()

    # Check each foreign key
    for fk in foreign_keys:
      ref_table = fk[2]  # Referenced table
      ref_column = fk[4]  # Referenced column
      from_column = fk[3]  # Column in the current table

      # Check if each value in the foreign key column exists in the referenced column of the referenced table
      cursor.execute(
        f"""
        SELECT COUNT(*) 
        FROM {table} 
        WHERE {from_column} NOT IN (SELECT {ref_column} FROM {ref_table})
        AND {from_column} IS NOT NULL;
        """
      )
      count = cursor.fetchone()[0]

      if count > 0:
        print(
          f"+ Integrity check failed: {count} record(s) in {table}.{from_column} not found in {ref_table}.{ref_column} ❌"
        )
      else:
        print(
          f"+ Integrity check passed for {table}.{from_column} referencing {ref_table}.{ref_column} ✅"
        )


if __name__ == "__main__":
  from pprint import pprint
  db = CrawlDatabase("../data/crawl_database.db")
  # SCHEMA TESTS
  result = test_referential_integrity(db)
  print(f"+ Referential integrity test ... {'passed ✅' if result else 'failed ❌'}")
  result = test_unique_constraint(db)
  print(f"+ Unique constraint test ... {'passed ✅' if result else 'failed ❌'}")

  # DATA INTEGRITY TESTS
  check_foreign_keys(db)
