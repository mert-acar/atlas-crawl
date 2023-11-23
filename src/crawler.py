import re
import pandas as pd
from tqdm import tqdm
from io import StringIO
from database import CrawlDatabase
from argparse import ArgumentParser
from typing import Union, Any, Callable

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

URL = "https://yokatlas.yok.gov.tr/{year}/lisans-panel.php?y={program_id}&p={table_id}"
tables = {"ranking": "1000_1", "highschools": "1060"}


def parse_arguments():
  """ Argument parser for the crawler CLI """
  parser = ArgumentParser(
    prog="AtlasCrawl🧭",
    description="Web crawler that scrapes tables from YÖK Atlas.",
    epilog="Bir kere rehber, daima rehber.",
  )
  parser.add_argument("year", help="Year to scrape", type=int)
  parser.add_argument("program_ids", help="Path to program ID file")
  parser.add_argument(
    "-d",
    "--database",
    default="../data/crawl_database.db",
    help="Path to the database file (Default ../data/crawl_database.db)"
  )
  parser.add_argument(
    "-tp",
    "--timeout-patience",
    default=5,
    type=int,
    help="Amount of seconds for the webdriver to wait for page to load"
  )
  args = parser.parse_args()
  return args


def find_element(element_xpath: str, timeout_patience: int = 5, func: Union[Callable, None] = None):
  """
  Return the element by xpath. Can run function on it if func argument is passed.

  Parameters
  ----------
  element_xpath
    The xpath of the element to be found

  func
    Function to run on the found element

  Returns
  -------
  element
    Desired element handle in selenium 

  Raises
  ------
  TimeoutException
    When the element cannot be found in designated patience, it raises this exception
  NoSuchElementException
    If the element you are looking for does not exist, it raises this exception
  """
  element = WebDriverWait(browser, timeout_patience).until(
    EC.presence_of_element_located((By.XPATH, element_xpath))
  )
  if func is not None:
    element = func(element)
  return element


def parse_rankings(dfs: list[pd.DataFrame], year) -> dict:
  """
  Parse general ranking table from HTML

  Parameters
  ----------
  dfs
    Pandas parses the HTML into a standard DF. Pass it here to make it suitable for
    the database.

  Returns
  -------
  out
    dictionary of the parsed data
  """
  dept_name = dfs[0].columns[0]

  # Some pages have extra promotional tables at the end.
  if len(dfs) == 4:
    dfs = dfs[:-1]

  standardized_dfs = [
    df.rename(columns={
      df.columns[0]: 'Column1',
      df.columns[1]: 'Column2'
    }) for df in dfs
  ]

  df = pd.concat(standardized_dfs, ignore_index=True).map(str).replace("---", "").replace("Dolmadı", "")
  data_dict = df.set_index("Column1")["Column2"].to_dict()
  out = {
    "uni_name":
      data_dict["Üniversite"],
    "uni_type":
      "State" if data_dict["Üniversite Türü"] == "Devlet" else "Private",
    "fac_name":
      data_dict["Fakülte / Yüksekokul"],
    "dept_id":
      data_dict["ÖSYM Program Kodu"],
    "dept_name":
      dept_name.replace("(" + data_dict["Burs Türü"] + ")", "").strip(),
    "dept_type":
      data_dict["Puan Türü"],
    "scholarship":
      data_dict["Burs Türü"].replace("%", "").split()[0].replace("İÖ-", ""),
    "total_quota":
      data_dict["Toplam Kontenjan"],
    "total_placed":
      data_dict["Toplam Yerleşen"],
    "min_points":
      data_dict["0,12 Katsayı ile Yerleşen Son Kişinin Puanı*"],
    "max_points":
      data_dict[f"{year} Tavan Puan(0,12)*"],
    "min_ranking":
      data_dict["0,12 Katsayı ile Yerleşen Son Kişinin Başarı Sırası*"].replace('.', ''),
    "max_ranking":
      data_dict[f"{year} Tavan Başarı Sırası(0,12)*"].replace(".", ""),
  }
  return {k: v if v != "" else None for k, v in out.items()}


def parse_highschools(df: pd.DataFrame) -> pd.DataFrame:
  """
  Parse high school table read from HTML

  Parameters
  ----------
  df
    Pandas parses the HTML into a standard DF. Pass it here to make it suitable for
    the database.

  Returns
  -------
  parsed_df
  """
  # Replace no grad symbol to 0
  df = df[0].replace("---", 0)
  # Drop the merged title cells in the table
  df.columns = df.columns.droplevel()
  if len(df) == 0:
    # If after the modifications no rows remain the program is empty
    return df
  # Remove Toplam row
  df = df.loc[df['Lise'] != "Toplam"].reset_index(drop=True)

  # Parser func to apply to each row
  def parser_func(row):
    hs_name = row["Lise"]
    # Extract city an districts from the hs name string
    # definetely needs refactor. very ugly
    idxx = hs_name[::-1].find("(")
    location = hs_name[len(hs_name) - idxx:-1]
    pure_name = hs_name[:len(hs_name) - idxx - 1].strip()
    location = location.split(" - ")
    if pure_name == "AÇIK ÖĞRETİM LİSESİ":
      city = "AÇIK ÖĞRETİM LİSESİ"
    else:
      city = location[0]
    if len(location) > 1:
      district = location[1]
    else:
      district = "MERKEZE BAĞLI TAŞRA"

    out = pd.Series(
      [
        pure_name,
        city,
        district,
        row["Lise'den Yeni Mezun"],
        row["Önceki Mezun"],
      ],
      index=['hs', 'hs_city', 'hs_district', 'new_grad', 'old_grad']
    )
    return out

  df = df.apply(parser_func, axis=1, result_type="expand")
  return df


def crawl_program(idx: str, year: int):
  """
  Crawl the program page for the rankings and high school placements

  Parameters
  ==========
  idx
    The program id assigned by the Council of Higher Education

  year
    The year for which the placement data will be crawled

  Returns
  =======
  rankings
    A dictionary describing the ranking data like total quota, total placed,
    minimum ranking etc.

  highschool
    A pandas data frame describing the placement table
  """
  url = URL.format(year=year, program_id=idx, table_id=tables["ranking"])
  browser.get(url)
  # Get the university city
  city = find_element(
    "/html/body/div[1]/div/div/div[2]/div/h3[1]", timeout_patience=args.timeout_patience
  ).text
  # Regular expression magic
  city = re.findall(r'\(([^)]+)\)', city)[-1]

  # Get the ranking table
  table = find_element(
    f'//*[@id="icerik_{tables["ranking"]}"]', timeout_patience=args.timeout_patience
  )
  # Wait for the table to load
  find_element(
    f'//*[@id="icerik_{tables["ranking"]}"]/table', timeout_patience=args.timeout_patience
  )

  # Parse the table using pandas so that python can read it
  df = pd.read_html(StringIO(table.get_attribute("outerHTML")), thousands='.', decimal=',')
  # Parse the tables into useful information
  rankings = parse_rankings(df, args.year)
  rankings.update({"uni_city": city, "year": year})

  # Go to the high schools site
  url = URL.format(year=year, program_id=idx, table_id=tables["highschools"])
  browser.get(url)

  # Get the high schools table
  table = find_element(
    f'//*[@id="icerik_{tables["highschools"]}"]', timeout_patience=args.timeout_patience
  )
  # Wait for the table to load
  find_element(
    f'//*[@id="icerik_{tables["highschools"]}"]/table', timeout_patience=args.timeout_patience
  )

  # Parse the table using pandas so that python can read it
  df = pd.read_html(StringIO(table.get_attribute("outerHTML")))
  # Parse the tables into useful information
  highschools = parse_highschools(df)
  return rankings, highschools


if __name__ == "__main__":
  from pprint import pprint

  # Get the command line arguments
  args = parse_arguments()

  # Create the web driver to crawl
  options = webdriver.chrome.options.Options()
  options.add_argument("--headless")
  service = webdriver.chrome.service.Service(executable_path="./chromedriver")
  browser = webdriver.Chrome(options=options, service=service)

  # Connect to the database
  db = CrawlDatabase(args.database)

  # Read the program ids
  with open(args.program_ids, "r") as f:
    programs = list(map(lambda x: x.strip(), f.readlines()))

  pbar = tqdm(programs)
  # pbar = tqdm(programs[136:138])
  for idx in pbar:
    ranking_data, highschool_data = crawl_program(idx, args.year)
    # pbar.set_description(f"{ranking_data['uni_name']} / {ranking_data['dept_name']}")
    pprint(ranking_data)
    db.write_rankings(ranking_data)
    if len(highschool_data) != 0:
      db.write_highschools(highschool_data, idx, args.year)
  browser.close()
  db.close()