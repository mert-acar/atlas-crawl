import os
import pandas as pd
import streamlit as st
import plotly.express as px
from database import CrawlDatabase


@st.cache_resource
def get_database_session():
  # Create a database session object that points to the URL.
  return CrawlDatabase("../data/crawl_database.db")


def prog_id_to_prog_name(x):
  return next(
    (
      f"{row['UniversityName']} / {row['ProgramName']} [{row['ScholarshipType']}]"
      for _, row in programs.iterrows() if row['ProgramID'] == x
    )
  )

def plot_rankings_across_years(rankings):
  rankings["ProgramString"] = rankings['ProgramID'].map(prog_id_to_prog_name)

  ranking_data_long = pd.melt(
    rankings,
    id_vars=['Year', 'ProgramString'],
    value_vars=['MinimumRanking', 'MaximumRanking'],
    var_name='RankType',
    value_name='Ranking'
  )

  # Creating Plotly chart
  fig = px.line(
    ranking_data_long,
    x="Year",
    y="Ranking",
    color="ProgramString",
    line_dash="RankType",
    markers=True,
    labels={
      "ProgramString": "Program",
      "Year": "Year",
      "Ranking": "Ranking",
      "RankType": "Rank Type"
    },
    title="Program Rankings Over Years"
  )

  # Update layout if necessary, e.g., legend position
  fig.update_layout(
    legend_title_text='Programs',
    legend=dict(orientation="h", yanchor="bottom", y=-0.7, xanchor="center", x=0.5),
    xaxis=dict(tickmode='array', tickvals=ranking_data_long['Year'].unique())
  )
  return fig


if __name__ == "__main__":
  ## =========================================================  ##
  ## ========================= SETUP =========================  ##
  ## =========================================================  ##
  # Title and logo
  st.set_page_config(layout="wide", page_title="Atlas Crawl 🧭")
  # st.sidebar.image("../data/logo.png", width=150)
  st.title("Atlas Crawl 🧭")
  db = get_database_session()

  # PROGRAM RANKINGS ACROSS YEARS
  # st.header("Program Rankings Across Years", divider='red')
  # universities = db.get_universities()
  # selected_uni_ids = st.multiselect(
  #   "Select Universities",
  #   universities['UniversityID'],
  #   format_func=lambda x: universities.loc[universities['UniversityID'] == x, 'UniversityName'].
  #   iloc[0]
  # )
  # if selected_uni_ids:
  #   programs = db.get_programs(selected_uni_ids)
  #   selected_program_ids = st.multiselect(
  #     "Select Programs", programs['ProgramID'], format_func=prog_id_to_prog_name
  #   )
  #   if selected_program_ids:
  #     rankings = db.get_rankings(selected_program_ids)
  #     rnew = rankings.copy()
  #     rnew["Year"] = 2020
  #     rnew2 = rankings.copy()
  #     rnew2["Year"] = 2021
  #     rankings = pd.concat((rankings, rnew, rnew2), ignore_index=True)
  #     fig = plot_rankings_across_years(rankings)
  #     st.plotly_chart(fig, use_container_width=True)
