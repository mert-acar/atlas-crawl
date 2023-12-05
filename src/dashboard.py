import os
import pandas as pd
import streamlit as st
from typing import Union
from yaml import full_load
from database import CrawlDatabase


@st.cache_resource
def get_database_session(path: Union[str, os.PathLike]):
  """ Create a database session object that points to the URL. """
  return CrawlDatabase(path)


@st.cache_data
def get_config(path: Union[str, os.PathLike]):
  """ Load config file """
  with open(path, "r") as f:
    config = full_load(f)
  return config


def filter_selections():
  """ IMPLEMENT THIS FUNCTION """
  pass 


def proper_string(text: str) -> str:
  """
  Correctly capitalizes a Turkish string where only the first character of each word is in uppercase.
  Turkish-specific characters are handled correctly.
  """
  # Turkish-specific lowercase conversions
  lowercase_map = {'I': 'ı', 'İ': 'i', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ'}

  # Split the text into words
  words = text.split()

  # Capitalize the first letter of each word and make the rest lowercase with Turkish rules
  capitalized_words = []
  for word in words:
    first_letter = word[0]
    # Special handling for Turkish 'I' and 'İ'
    if first_letter == 'I':
      first_letter = 'İ'
    rest = ''.join([lowercase_map.get(char, char.lower()) for char in word[1:]])
    capitalized_words.append(first_letter + rest)

  # Join the words back into a string and return
  return ' '.join(capitalized_words)


if __name__ == "__main__":
  st.set_page_config(layout="wide", page_title="Atlas Crawl 🧭")
  st.title("Atlas Crawl 🧭")
  ss = st.session_state
  config = get_config("configs.yaml")
  db = get_database_session(config["db_path"])

  with st.container(border=True):
    uni_data = db.get_uni_filter_data()
    hs_data = db.get_hs_filter_data()

    r1c1, r1c2 = st.columns(2)
    with r1c1:
      key = "City"
      city = st.multiselect(
        f"{key}:",
        options=pd.unique(hs_data[key]),
        key=key,
        format_func=proper_string
      )
    with r1c2:
      key = "District"
      district = st.multiselect(
        f"{key}:",
        options=pd.unique(hs_data[key]),
        key=key,
        format_func=proper_string
      )

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
      key = "University"
      uni = st.multiselect(
        f"{key}:",
        options=pd.unique(uni_data[f"{key}Name"]),
        key=key,
        default=config["uni_defaults"],
        format_func=proper_string
      )
    with r2c2:
      key = "Faculty"
      fac = st.multiselect(
        f"{key}:",
        options=pd.unique(uni_data[f"{key}Name"]),
        key=key,
        format_func=proper_string
      )
    with r2c3:
      key = "Program"
      dept = st.multiselect(
        f"{key}:",
        options=pd.unique(uni_data[f"{key}Name"]),
        key=key,
        format_func=proper_string
      )
