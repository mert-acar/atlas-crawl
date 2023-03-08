import os
import json
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st


def filter_uni_options(key):
  ss.uni_data = apply_filters()
  idx = uni_keys.index(key)
  keys = uni_keys[idx+1:]
  for k in keys:
    ss.uni_options[k] = pd.unique(ss.uni_data[k])


def apply_filters():
  keys = uni_keys
  mask = np.logical_and.reduce([
    ss.master_data[key].isin(ss[key]) for key in keys if len(ss[key]) != 0
  ])
  if isinstance(mask, np.bool_):
    return ss.master_data
  return ss.master_data[mask]


if __name__ == "__main__":
  st.set_page_config(layout="wide", page_title="BTO - AtlasCrawl")
  ss = st.session_state
  if "uni_loaded" not in ss:
    ss.uni_loaded = False
  if "nums" not in ss:
    ss.nums = {}

  uni_keys = ['uni_city', 'uni', 'fac', 'dept', 'scho']
  
  if "strings" in ss:
    strings = ss.strings
  else:
    with open("data/strings.json", "r") as f:
      strings = json.load(f)
  
  st.write(strings["title"])
  strings = strings["Analyze"]
  st.write(strings["message"])

  # Load Data
  # Here we create a streamlit form to avoid reading data at each widget interaction
  # This can also be achieved with cache funtion, however we also initialize other
  # variables here. Also any data we want to have persistenly across reruns are stored
  # in the session state variable [ss].
  root = "data/crawls"
  files = os.listdir(root)
  format_func = lambda x: x.split(".")[0] # Do not display the file extentions on selection menu
  with st.form("uni_data_selection"):
    st.write(strings["load_prompt"])
    col1, col2 = st.columns([0.93, 0.07]) # Place the button to the side
    info_place = st.empty()
    file_selection = col1.selectbox("aa", files, format_func=format_func, label_visibility="collapsed")
    submit = col2.form_submit_button(strings["load_button"])
    if submit:
      try:
        ss.master_data = pd.read_parquet(os.path.join(root, file_selection)) # Load the data
        # extract the options to be displayed on the filter menus
        ss.uni_options = {key: pd.unique(ss.master_data[key]) for key in ss.master_data.columns} 
        info_place.success(strings["load_success"])
        ss.uni_loaded = True
        ss.nums.update({
          'total_grad': ss.master_data['total_grad'].sum(),
          'total_hs': len(pd.unique(ss.master_data['hs'])),
          'total_unis': len(pd.unique(ss.master_data['uni'])),
          'uni': {
            'grad': ss.master_data['total_grad'].sum(),
            'hs': len(pd.unique(ss.master_data['hs'])),
            'unis': len(pd.unique(ss.master_data['uni']))
          }
        })
        ss.uni_data = ss.master_data
      except Exception as e:
        info_place.error(strings["load_error"] + ":\n" + str(e))
        raise SystemExit
        
  # filters
  if ss.uni_loaded:
    # Initially we dont use a filter and select everyting. With each change
    # trigger of below filters, we filter.
    st.write(strings["filter_prompt"])

    first_row = st.columns(2)
    with first_row[0]:
      st.multiselect(strings["uni_city"], ss.uni_options['uni_city'], on_change=filter_uni_options, args=['uni_city'], key='uni_city')
    with first_row[1]:
      st.multiselect(strings["uni"], ss.uni_options['uni'], on_change=filter_uni_options, args=['uni'], key='uni')

    second_row = st.columns(3)
    with second_row[0]:
      st.multiselect(strings["fac"], ss.uni_options['fac'], on_change=filter_uni_options, args=['fac'], key='fac')
    with second_row[1]:
      st.multiselect(strings["dept"], ss.uni_options['dept'], on_change=filter_uni_options, args=['dept'], key='dept')
    with second_row[2]:
      st.multiselect(strings["scho"], ss.uni_options['scho'], on_change=filter_uni_options, args=['scho'], key='scho')


    ss.nums['uni']['grad'] = ss.uni_data['total_grad'].sum()
    ss.nums['uni']['hs'] = len(pd.unique(ss.uni_data['hs']))
    ss.nums['uni']['unis'] = len(pd.unique(ss.uni_data['uni']))

    st.write(strings['current_selection'])
    cols = st.columns(3)
    with cols[0]:
      st.write(strings['num_students'].format(ss.nums['uni']['grad'], ss.nums['total_grad'], ss.nums['uni']['grad'] * 100 / ss.nums['total_grad']))
    with cols[1]:
      st.write(strings["num_uni"].format(ss.nums['uni']['unis'], ss.nums['total_unis'], ss.nums['uni']['unis'] * 100 / ss.nums['total_unis']))
    with cols[2]:
      st.write(strings["num_hs"].format(ss.nums['uni']['hs'], ss.nums['total_hs'], ss.nums['uni']['hs'] * 100 / ss.nums['total_hs']))
    data = ss.uni_data

    # We display 2 tabs. One for all the interactive charts and the other for the raw data
    chart, table = st.tabs(['Graph', 'Data'])
    with chart:
      c1, c2 = st.columns(2)
      num_hs = len(pd.unique(data['hs']))
      num_dept = len(pd.unique(data['dept']))
      if any(len(ss[key]) > 0 for key in uni_keys):
        st.write(strings['top_hs_prompt'])
        with c1:
          ## TOTAL GRAD HORIZONTAL BAR PLOT WITH TOP-K UNI SELECTION SLIDER
          num2show_hs = st.slider(strings['top_hs_slider'], 1, num_hs , 10 if 10 <= num_hs else num_hs // 2)   
          hs_chart = alt.Chart(data).transform_aggregate(
            aggregate_grad='sum(total_grad)',
            groupby=['hs'],
          ).transform_calculate(
            frac = alt.datum.aggregate_grad / ss.nums['uni']['grad']
          ).transform_window(
            rank='row_number()',
            sort=[alt.SortField("aggregate_grad", order="descending")],
          ).transform_filter(
            "datum.rank <= {}".format(num2show_hs)
          ).mark_bar().encode(
            x=alt.X('aggregate_grad:Q', aggregate='sum', title=strings['grad']),
            y=alt.Y('hs:N',sort="-x", title=strings['hs']),
            color=alt.value(strings['bilkent_blue']),
            tooltip=[
              alt.Tooltip("hs:N", title=strings['hs']),
              alt.Tooltip("aggregate_grad:Q", title=strings['grad']),
              alt.Tooltip("frac:Q", title=strings['grad_per'], format=".0%"),
            ]
          ).properties(
            title=strings['top_hs_title'].format(num2show_hs),
          )
          text = hs_chart.mark_text(
            align='left',
            baseline='middle',
            dx=3  # Nudges text to right so it doesn't appear on top of the bar
          ).encode(
            text='aggregate_grad:Q',
            color=alt.value("white")
          )
          st.altair_chart((hs_chart + text), True)

          ## INDIVIDUAL HIGHSCHOOL GRADUATES BY PREFERED UNIVERSITIES
          st.write(strings['spec_hs_info'])
          hs_selection = st.selectbox(strings['spec_hs_prompt'], pd.unique(data['hs'])) 
          merge = st.checkbox(strings['aggregated_checkbox'], value=True)
          if merge:
            base = alt.Chart(data).transform_filter(
              alt.datum.hs == hs_selection
            ).transform_aggregate(
              aggregate_grad='sum(total_grad)',
              groupby=['dept'],
            ).encode(
              theta=alt.Theta("aggregate_grad:Q", stack=True),
              radius=alt.Radius("aggregate_grad:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=70)),
              color=alt.Color("dept:N", legend=None),
              tooltip=[
                alt.Tooltip("dept:N", title=strings['dept']),
                alt.Tooltip("aggregate_grad:Q", title=strings['grad'])
              ]
            )

            line1 = base.mark_arc(innerRadius=40 , stroke="#fef").properties(
              title=strings['aggregated_grad_title_dept']
            )
            line2 = base.mark_text(radiusOffset=10, size=14).encode(text="aggregate_grad:Q")
            st.altair_chart((line1 + line2), True)

          else:
            charts = alt.vconcat()
            for scho in pd.unique(data['scho']):
              if len(data.loc[(data['scho'] == scho) & (data['hs'] == hs_selection)]) != 0:
                base = alt.Chart(data).transform_filter(
                  (alt.datum.hs == hs_selection) & (alt.datum.scho == scho)
                ).transform_aggregate(
                  aggregate_grad='sum(total_grad)',
                  groupby=['dept'],
                ).encode(
                  theta=alt.Theta("aggregate_grad:Q", stack=True),
                  color=alt.Color("dept:N", legend=None),
                  tooltip=[
                    alt.Tooltip("dept:N", title=strings['dept']),
                    alt.Tooltip("aggregate_grad:Q", title=strings['grad'])
                  ]
                )
                if scho >= 0:
                  t = strings['individual_scho'].format(scho)
                else:
                  t = strings['individual_scho_state']
                line1 = base.mark_arc(innerRadius=40 , stroke="#fef").properties(
                  title=strings['individual_scho_title'].format(t)
                )
                charts &= line1
            st.altair_chart(charts, False)


            
        with c2:
          ## TOPK DEPARTMENTS BY GRADUATE PREFERENCE
          num2show_dept = st.slider(strings['top_dept_slider'], 1, num_dept , 10 if 10 <= num_dept else num_dept // 2)   
          dept_chart = alt.Chart(data).transform_aggregate(
            aggregate_grad='sum(total_grad)',
            groupby=['dept'],
          ).transform_window(
            rank='row_number()',
            sort=[alt.SortField("aggregate_grad", order="descending")],
          ).transform_filter(
            "datum.rank <= {}".format(num2show_dept)
          ).transform_calculate(
            frac = alt.datum.aggregate_grad / ss.nums['uni']['grad']
          ).mark_bar().encode(
            x=alt.X('aggregate_grad:Q', aggregate='sum', title="Total Graduate"),
            y=alt.Y('dept:N',sort="-x", title=strings['dept']),
            color=alt.value(strings['bilkent_blue']),
            tooltip=[
              alt.Tooltip("dept:N", title=strings['dept']),
              alt.Tooltip("aggregate_grad:Q", title=strings['grad']),
              alt.Tooltip("frac:Q", title=strings['grad_per'], format=".0%"),
            ]
          ).properties(
            title=strings['top_dept_title'].format(num2show_dept)
          )
          text = dept_chart.mark_text(
            align='left',
            baseline='middle',
            dx=3  # Nudges text to right so it doesn't appear on top of the bar
          ).encode(
            text='aggregate_grad:Q',
            color=alt.value("white")
          )
          st.altair_chart((dept_chart+text),True)

          ## INDIVIDUAL DEPARTMENT BY HIGHSCHOOL
          st.write(strings['spec_dept_info'])
          dept_selection = st.multiselect(strings['spec_dept_prompt'], pd.unique(data['dept'])) 
          if len(dept_selection) > 0:
            dept_merge = st.checkbox(strings['aggregated_checkbox'], value=True, key='dept_merge')
            if dept_merge:
              dept_base = alt.Chart(data).transform_filter(
                alt.FieldOneOfPredicate(field='dept', oneOf=dept_selection)
              ).transform_aggregate(
                aggregate_grad='sum(total_grad)',
                groupby=['hs'],
              ).encode(
                theta=alt.Theta("aggregate_grad:Q", stack=True),
                radius=alt.Radius("aggregate_grad:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=70)),
                color=alt.Color("hs:N", legend=None),
                tooltip=[
                  alt.Tooltip("hs:N", title=strings['hs']),
                  alt.Tooltip("aggregate_grad:Q", title=strings['grad'])
                ]
              )

              line1 = dept_base.mark_arc(innerRadius=40 , stroke="#fef").properties(
                title=strings['aggregated_grad_title_uni']
              )
              line2 = dept_base.mark_text(radiusOffset=10, size=14).encode(text="aggregate_grad:Q")
              st.altair_chart((line1 + line2), True)
            else:
              charts = alt.vconcat()
              for scho in pd.unique(data['scho']):
                if len(data.loc[(data['scho'] == scho) & (data['dept'].isin(dept_selection))]) != 0:
                  base = alt.Chart(data).transform_filter(
                    alt.FieldOneOfPredicate(field='dept', oneOf=dept_selection)
                  ).transform_filter(
                    alt.FieldEqualPredicate(field='scho', equal=scho)
                  ).transform_aggregate(
                    aggregate_grad='sum(total_grad)',
                    groupby=['hs'],
                  ).encode(
                    theta=alt.Theta("aggregate_grad:Q", stack=True),
                    color=alt.Color("hs:N", legend=None),
                    tooltip=[
                      alt.Tooltip("hs:N", title=strings['hs']),
                      alt.Tooltip("aggregate_grad:Q", title=strings['grad'])
                    ]
                  )
                  if scho >= 0:
                    t = strings['individual_scho'].format(scho)
                  else:
                    t = strings['individual_scho_state']
                  line1 = base.mark_arc(innerRadius=40 , stroke="#fef").properties(
                    title=strings['individual_scho_title'].format(t)
                  )
                  charts &= line1
              st.altair_chart(charts, False)
      

        ## CITY DISTRIBUTION
        d = data.groupby("hs_city").agg({"total_grad": "sum"}).reset_index()
        d.loc[d['total_grad'] < ss['nums']['uni']['grad'] * 0.04, "hs_city"] = 'All Others'
        d = d.groupby("hs_city").agg({"total_grad": "sum"}).reset_index()
        d['dummy'] = 'City'
        hs_city_chart = alt.Chart(d).transform_calculate(
          frac = alt.datum.total_grad / ss['nums']['uni']['grad']
        ).mark_bar().encode(
          x=alt.X('total_grad:Q', stack="normalize", title=None),
          row=alt.Row('dummy:N', title=None),
          color=alt.Color(
            'hs_city:N',
            legend=alt.Legend(
              orient='bottom',
              direction='horizontal',
            ),
            title=None
          ),
          tooltip=[
            alt.Tooltip("hs_city:N", title=strings['hs_city']),
            alt.Tooltip("total_grad:Q", title=strings['grad']),
            alt.Tooltip("frac:Q", title=strings['grad_per'], format=".0%"),
          ]
        ).configure_axis(
          grid=False
        ).properties(title=strings['city_distribution'], height=100)
        st.altair_chart(hs_city_chart, True)
    with table:
      st.dataframe(data)
