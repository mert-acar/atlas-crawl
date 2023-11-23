""" Test script for database validation during schema development """

from database import CrawlDatabase
from sqlite3 import Error, IntegrityError


def test_unique_constraint(db):
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


def test_referential_integrity(db):
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


if __name__ == "__main__":
  with open("./schema.sql", "r") as f:
    schema = f.read()
  db = CrawlDatabase.create_from_schema(schema=schema, path=":memory:")

  # TESTS
  result = test_referential_integrity(db)
  print(f"+ Referential integrity test ... {'passed ✅' if result else 'failed ❌'}")
  result = test_unique_constraint(db)
  print(f"+ Unique constraint test ... {'passed ✅' if result else 'failed ❌'}")

  db.close()
