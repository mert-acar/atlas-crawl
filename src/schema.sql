-- University Table
CREATE TABLE University (
    UniversityID INTEGER PRIMARY KEY,
    UniversityName TEXT NOT NULL UNIQUE,
    UniversityType TEXT CHECK(UniversityType IN ('Private', 'State')),
    UniversityCity TEXT NOT NULL
);

-- Faculty Table
CREATE TABLE Faculty (
    FacultyID INTEGER PRIMARY KEY,
    UniversityID INTEGER NOT NULL,
    FacultyName TEXT NOT NULL,
    UNIQUE (UniversityID, FacultyName),
    FOREIGN KEY (UniversityID) REFERENCES University(UniversityID)
);

-- Program Table
CREATE TABLE Program (
    ProgramID INTEGER PRIMARY KEY,
    FacultyID INTEGER NOT NULL,
    ProgramName TEXT NOT NULL,
    ScholarshipType TEXT,
    ProgramType TEXT CHECK(ProgramType IN ('SAY', 'SOZ', 'DIL', 'EA')),
    UNIQUE (FacultyID, ProgramName, ScholarshipType, ProgramType),
    FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID)
);

-- PlacementData Table
CREATE TABLE PlacementData (
    ProgramID INTEGER NOT NULL,
    Year INTEGER NOT NULL,
    LowestScore REAL,
    HighestScore REAL,
    TotalQuota INTEGER NOT NULL,
    TotalPlaced INTEGER,
    MaximumRanking INTEGER,
    MinimumRanking INTEGER,
    FOREIGN KEY (ProgramID) REFERENCES Program(ProgramID),
    PRIMARY KEY (ProgramID, Year)
);

-- HighSchool Table
CREATE TABLE HighSchool (
    HighSchoolID INTEGER PRIMARY KEY,
    HighSchoolName TEXT NOT NULL,
    City TEXT NOT NULL,
    District TEXT NOT NULL,
    Score REAL, 
    CounselorName TEXT,
    CounselorPhone TEXT,
    CounselorEmail TEXT,
    UNIQUE (HighSchoolName, City, District)
);

-- HighSchoolPlacement Table
CREATE TABLE HighSchoolPlacement (
    HighSchoolID INTEGER NOT NULL,
    ProgramID INTEGER NOT NULL,
    Year INTEGER NOT NULL,
    NumberOfNewGrads INTEGER NOT NULL,
    NumberOfOldGrads INTEGER NOT NULL,
    FOREIGN KEY (HighSchoolID) REFERENCES HighSchool(HighSchoolID),
    FOREIGN KEY (ProgramID) REFERENCES Program(ProgramID),
    PRIMARY KEY (HighSchoolID, ProgramID, Year)
);
