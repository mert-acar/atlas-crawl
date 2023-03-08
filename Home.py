import os
import json
import random
import streamlit as st

with open("data/strings.json", "r") as f:
  strings = json.load(f)

st.set_page_config(layout="wide", page_title="BTO - AtlasCrawl")
st.session_state['strings'] = strings

st.write(strings['title'])
c1, _,  c2 = st.columns([0.4,0.2, 0.4])
st.sidebar.success(strings['Home']['sidebar_success'])
with c1:
  st.markdown(strings['Home']['message'])

with c2:
  try:
    with open("data/lit.json", "r") as f:
      lit = json.load(f)
    st.markdown("#### _Literature Corner_")
    author = random.choice(list(lit.keys()))
    content = random.choice(lit[author]).replace("\\n", "\n")
    st.markdown(content)
    st.markdown("_" + author + "_")
  except FileNotFoundError:
    st.image("figures/logo.png", use_column_width=True)
