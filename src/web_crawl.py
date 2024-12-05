import re
import time
import pandas as pd
from pandas.core.algorithms import rank
from yaml import full_load
from datetime import datetime
from typing import Union, Tuple
from argparse import ArgumentParser, Namespace

# SELENIUM
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

# custom code
from db_manager import AtlasDBManager


def parse_arguments() -> Namespace:
  """ Argument parser for the crawler CLI """
  parser = ArgumentParser(
    prog="AtlasCrawl🧭",
    description="Web crawler that scrapes tables from YÖK Atlas.",
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
    "-b",
    "--browser",
    default="chrome",
    help="browser to use for page requests. Supports one of [chrome, firefox]"
  )
  parser.add_argument(
    "-tp",
    "--timeout-patience",
    default=5,
    type=int,
    help="Amount of seconds for the webdriver to wait for page to load"
  )
  parser.add_argument(
    "--override",
    action="store_true",
    help="If set override the values in the database. Otherwise the value is skipped"
  )
  args = parser.parse_args()
  return args


def build_url(year: int, program_id: int, table_id: str) -> str:
  url = "https://yokatlas.yok.gov.tr/{year}/lisans-panel.php?y={program_id}&p={table_id}"
  return url.format(
    year=year, program_id=program_id, table_id=table_id
  ).replace(f"{datetime.now().year}/", "")


def find_element(
  browser: Union[webdriver.Chrome, webdriver.Firefox],
  element_xpath: str,
  timeout_patience: int = 5,
):
  element = WebDriverWait(browser, timeout_patience).until(
    EC.presence_of_element_located((By.XPATH, element_xpath))
  )
  return element


if __name__ == "__main__":
  from tqdm import tqdm
  from pprint import pprint

  # Get the command line arguments
  args = parse_arguments()

  if args.browser == "chrome":
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    browser = webdriver.Chrome(options=options)
  elif args.browser == "firefox":
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    browser = webdriver.Firefox(options=options)
  else:
    raise NotImplementedError(f"Browser not implemented: {args.browser}")

  db = AtlasDBManager(args.database)

  with open("xpath_map.yaml", "r") as f:
    xpath_map = full_load(f)

  # Read the program ids
  with open(args.program_ids, "r") as f:
    programs = list(map(lambda x: x.strip(), f.readlines()))

  pbar = tqdm(programs)
  for idx in pbar:
    if not db.placement_data_exists(idx, args.year) or args.override:
      # results = crawl_program(browser, idx, args.year, args.timeout_patience)
      year = args.year
      timeout_patience = args.timeout_patience


      url = build_url(year, idx, xpath_map["ranking"]["table_id"])
      for attempt in range(3):
        try:
          browser.get(url)

          # Get the university city
          city = find_element(
            browser, xpath_map["city_string"], timeout_patience=timeout_patience
          ).text

          # Regular expression magic
          city = re.search(r"(?<=\().*?(?=\))", city).group(0).strip()

          # Get the ranking table
          table = find_element(
            browser, xpath_map["ranking"]["table_xpath"], timeout_patience=timeout_patience
          )

          # Wait for the table to load
          find_element(
            browser,
            xpath_map["ranking"]["table_xpath"] + "/table",
            timeout_patience=timeout_patience
          )
          break
        except TimeoutException:
          time.sleep(0.3)
          continue
      else:
        raise Exception("Could not crawl program: {idx, year}")

      rankings = {"uni_city": city, "year": year, "dept_id": idx}
      for key, xpath in xpath_map["ranking"]["element_xpaths"].items():
        rankings[key] = str(table.find_element(By.XPATH, xpath).text).strip().replace("---", "").replace("Dolmadı", "").replace("*", "")
      rankings["dept_name"] = rankings["dept_name"].replace(f"({rankings['scholarship']})", "")

      url = build_url(year, idx, xpath_map["highschools"]["table_id"])
      for attempt in range(3):
        try:
          browser.get(url)

          # Get the ranking table
          table = find_element(
            browser, xpath_map["highschools"]["table_xpath"], timeout_patience=timeout_patience
          )

          # Wait for the table to load
          find_element(
            browser,
            xpath_map["highschools"]["table_xpath"] + "/table",
            timeout_patience=timeout_patience
          )
          break
        except TimeoutException:
          time.sleep(0.3)
          continue
      else:
        raise Exception("Could not crawl highschools from program: {idx, year}")
