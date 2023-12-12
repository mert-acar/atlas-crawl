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


def filter_selections(key: str):
  data = uni_data
  keys = "uni_keys"
  if "hs_" in key:
    data = hs_data
    keys = "hs_keys"

  idx = ss[keys].index(key) + 1
  for k in ss[keys][idx:]:
    if len(ss[key]) != 0:
      ss["options"][f"{k}_options"] = pd.unique(data.loc[data[key].isin(ss[key]), k])


def proper_string(text: str) -> str:
  """
  Correctly capitalizes a Turkish string where only the first character
  of each word is in uppercase. Turkish-specific characters are handled
  correctly.
  """
  # Turkish-specific lowercase conversions
  lowercase_map = {'I': 'ı', 'İ': 'i', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ'}

  # Split the text into words
  words = text.split()

  # Capitalize the first letter of each word and make the rest
  # lowercase with Turkish rules
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

  uni_data = db.get_uni_filter_data()
  hs_data = db.get_hs_filter_data()

  if "options" not in ss:
    ss["hs_keys"] = ["hs_city", "hs_district", "hs_name"]
    ss["uni_keys"] = [
      "uni_type", "uni_city", "uni_name", "fac_name", "prog_type", "program", "scholarship"
    ]
    ss["options"] = {f"{k}_options": sorted(pd.unique(uni_data[k])) for k in ss["uni_keys"]}
    ss["options"].update({f"{k}_options": sorted(pd.unique(hs_data[k])) for k in ss["hs_keys"]})

  s = 0.3
  filter_col, data_col = st.columns([s, 1 - s])
  with filter_col:
    # with st.form("filters"):
    with st.container(border=True):
      st.write("High School Filters")
      key = "hs_city"
      city = st.multiselect(
        "City:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )

      key = "hs_district"
      district = st.multiselect(
        "District:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, ),
        disabled=len(city) == 0
      )

      key = "hs_name"
      city = st.multiselect(
        "High Schools:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )

    with st.container(border=True):
      st.write("Year")
      start_year, end_year = st.select_slider(
        "Year", options=list(range(2019, 2024)), value=(2019, 2023), label_visibility="collapsed"
      )

    with st.container(border=True):
      st.write("University Filters")

      key = "uni_type"
      uni_type = st.multiselect(
        "Type:",
        options=ss["options"][f"{key}_options"],
        default=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )
      filter_selections(key)

      key = "uni_city"
      uni_city = st.multiselect(
        "City:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )

      key = "uni_name"
      uni = st.multiselect(
        "University:",
        options=ss["options"][f"{key}_options"],
        key=key,
        default=config["uni_defaults"] if all(t in uni_type for t in ["Private", "State"]) else [],
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )
      filter_selections(key)

      key = "fac_name"
      fac = st.multiselect(
        "Faculty:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )

      key = "prog_type"
      prog_type = st.multiselect(
        "Program Type:",
        options=ss["options"][f"{key}_options"],
        key=key,
        default=config["prog_type_defaults"],
        on_change=filter_selections,
        args=(key, )
      )
      filter_selections(key)

      key = "program"
      prog = st.multiselect(
        "Program:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )

      key = "scholarship"
      scho = st.multiselect(
        "Scholarship:",
        options=ss["options"][f"{key}_options"],
        key=key,
        format_func=proper_string,
        on_change=filter_selections,
        args=(key, )
      )
      submitted = st.button("Filter", type="primary", use_container_width=True)

  if submitted:
    with data_col:
      with st.spinner("Loading data..."):
        df = db.get_chart_data()
        df = df[df["year"].isin(list(range(start_year, end_year + 1)))]
      st.success("Done.")
      table, charts = st.tabs(["Table", "Charts"])
      with table:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Universities", value=f"🏛️ {len(pd.unique(df['uni_name']))}")
        c2.metric(
          "Programs", value=f"📓 {len(df.drop_duplicates(subset=['program', 'scholarship']))}"
        )
        c3.metric("High Schools", value=f"🎒 {len(pd.unique(df['hs_name']))}")
        c4.metric("Graduates", value=f"🎓 {(df['old_grad'] + df['new_grad']).sum()}")
        st.dataframe(
          df,
          height=1000,
          column_config={"year": st.column_config.NumberColumn("Year", format="%d")}
        )
