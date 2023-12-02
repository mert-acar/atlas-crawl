import pandas as pd
import streamlit as st
from database import CrawlDatabase


@st.cache_resource
def get_database_session():
  # Create a database session object that points to the URL.
  return CrawlDatabase("../data/crawl_database.db")


if __name__ == "__main__":
  st.set_page_config(layout="wide", page_title="Atlas Crawl 🧭")
  st.title("Atlas Crawl 🧭")
  db = get_database_session()
