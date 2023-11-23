import numpy as np
import pandas as pd
from tqdm import tqdm
from database import CrawlDatabase

def func(x):
  return 30000 / (x ** 0.5) 

def regress(x, lmbda):
  h = [x[0]]
  for n in range(1, len(x)):
    h_n = (1 - lmbda) * h[n - 1] + lmbda * x[n]
    h.append(h_n)
  return h


if __name__ == "__main__":
  db = CrawlDatabase("../data/crawl_database.db")
  highschools = db.query("SELECT * FROM HighSchool")
  placement_query = """
  SELECT 
    h.HighSchoolID, 
    h.HighSchoolName,
    pd.MinimumRanking,
    pd.MaximumRanking,
    hsp.Year, 
    (hsp.NumberOfNewGrads + hsp.NumberOfOldGrads) as TotalGrad
  FROM HighSchool h
    JOIN HighSchoolPlacement hsp ON h.HighSchoolID = hsp.HighSchoolID
    JOIN PlacementData pd ON pd.ProgramID = hsp.ProgramID AND pd.Year = hsp.Year
  WHERE h.HighSchoolID = {hsid}
  """
  pbar = tqdm(highschools.iterrows(), total=len(highschools))
  for i, row in pbar:
    hs_id = row["HighSchoolID"]
    df = db.query(placement_query.format(hsid=hs_id))
    print(len(df))
    break
    """
    scores = []
    for year in np.sort(pd.unique(df["Year"])):
      total = df.loc[df["Year"] == year, "TotalGrad"].sum()
      if total == 0:
        print(df)
        raise SystemExit
      val = (
        df.loc[df["Year"] == year, "MinimumRanking"].apply(func) *
        df.loc[df["Year"] == year, "TotalGrad"]
      ).sum()
      scores.append(val/total)
    score = regress(scores, 0.7)[-1]
    pbar.set_description(f"{df['HighSchoolName'].iloc[0]}: {score}")
    highschools.loc[highschools["HighSchoolID"] == hs_id, "Score"] = score
    """
