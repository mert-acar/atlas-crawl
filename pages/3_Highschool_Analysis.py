import os
import json
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st


def filter_hs_options(key):
  ss.hs_data = apply_filters()
  idx = hs_keys.index(key)
  keys = hs_keys[idx+1:]
  for k in keys:
    ss.hs_options[k] = pd.unique(ss.hs_data[k])


def apply_filters():
  keys = hs_keys
  mask = np.logical_and.reduce([
    ss.master_data[key].isin(ss[key]) for key in keys if len(ss[key]) != 0
  ])
  if isinstance(mask, np.bool_):
    return ss.master_data
  return ss.master_data[mask]


if __name__ == "__main__":
  st.set_page_config(layout="wide", page_title="BTO - AtlasCrawl")
  ss = st.session_state
  if "loaded" not in ss:
    ss.loaded = False
  if "nums" not in ss:
    ss.nums = {}

  hs_keys = ['hs_city', 'hs_district', 'hs']
  
  if "strings" in ss:
    strings = ss.strings
  else:
    with open("data/strings.json", "r") as f:
      strings = json.load(f)
  
  st.write(strings["title"])
  strings = strings["Analyze"]
  st.write(strings["hs_message"])

  # Load Data
  root = "data/crawls"
  files = os.listdir(root)
  format_func = lambda x: x.split(".")[0]
  with st.form("data_selection"):
    st.write(strings["load_prompt"])
    col1, col2 = st.columns([0.93, 0.07])
    info_place = st.empty()
    file_selection = col1.selectbox("aa", files, format_func=format_func, label_visibility="collapsed")
    submit = col2.form_submit_button(strings["load_button"])
    if submit:
      try:
        ss.master_data = pd.read_parquet(os.path.join(root, file_selection))
        ss.hs_options = {key: pd.unique(ss.master_data[key]) for key in ss.master_data.columns}
        info_place.success(strings["load_success"])
        ss.loaded = True
        ss.nums.update({
          'total_grad': ss.master_data['total_grad'].sum(),
          'total_hs': len(pd.unique(ss.master_data['hs'])),
          'total_unis': len(pd.unique(ss.master_data['uni'])),
          'hs': {
            'grad': ss.master_data['total_grad'].sum(),
            'hs': len(pd.unique(ss.master_data['hs'])),
            'unis': len(pd.unique(ss.master_data['uni']))
          }
        })
        ss.hs_data = ss.master_data
      except Exception as e:
        info_place.error(strings["load_error"] + ":\n" + str(e))
        raise SystemExit
        
  # filters
  if ss.loaded:
    # Initially we dont use a filter and select everyting. With each change
    # trigger of below filters, we filter.
    st.write(strings["filter_prompt"])

    first_row = st.columns(3)
    with first_row[0]:
      st.multiselect(strings["hs_city"], ss.hs_options['hs_city'], on_change=filter_hs_options, args=['hs_city'], key='hs_city')
    with first_row[1]:
      st.multiselect(strings["district"], ss.hs_options['hs_district'], on_change=filter_hs_options, args=['hs_district'], key='hs_district')
    with first_row[2]:
      st.multiselect(strings["hs"], ss.hs_options['hs'], on_change=filter_hs_options, args=['hs'], key='hs')


    ss.nums['hs']['grad'] = ss.hs_data['total_grad'].sum()
    ss.nums['hs']['hs'] = len(pd.unique(ss.hs_data['hs']))
    ss.nums['hs']['unis'] = len(pd.unique(ss.hs_data['uni']))

    st.write(strings['current_selection'])
    cols = st.columns(3)
    with cols[0]:
      st.write(strings['num_students'].format(ss.nums['hs']['grad'], ss.nums['total_grad'], ss.nums['hs']['grad'] * 100 / ss.nums['total_grad']))
    with cols[1]:
      st.write(strings["num_uni"].format(ss.nums['hs']['unis'], ss.nums['total_unis'], ss.nums['hs']['unis'] * 100 / ss.nums['total_unis']))
    with cols[2]:
      st.write(strings["num_hs"].format(ss.nums['hs']['hs'], ss.nums['total_hs'], ss.nums['hs']['hs'] * 100 / ss.nums['total_hs']))

    chart, table = st.tabs(['Graph', 'Data'])
    data = ss.hs_data

    with chart:
      c1, c2 = st.columns(2)
      num_unis = len(pd.unique(data['uni']))
      num_dept = len(pd.unique(data['dept']))
      if any(len(ss[key]) > 0 for key in hs_keys):
        st.write(strings['top_uni_prompt'])
        with c1:
          ## TOTAL GRAD HORIZONTAL BAR PLOT WITH TOP-K UNI SELECTION SLIDER
          num2show_uni = st.slider(strings['top_uni_slider'], 1, num_unis , 10 if 10 <= num_unis else num_unis // 2)   
          uni_chart = alt.Chart(data).transform_aggregate(
            aggregate_grad='sum(total_grad)',
            groupby=['uni'],
          ).transform_calculate(
            frac = alt.datum.aggregate_grad / ss.nums['hs']['grad']
          ).transform_window(
            rank='row_number()',
            sort=[alt.SortField("aggregate_grad", order="descending")],
          ).transform_filter(
            "datum.rank <= {}".format(num2show_uni)
          ).mark_bar().encode(
            x=alt.X('aggregate_grad:Q', aggregate='sum', title=strings["grad"]),
            y=alt.Y('uni:N',sort="-x", title=strings["uni"]),
            color=alt.condition(
              alt.datum.uni == "İHSAN DOĞRAMACI BİLKENT ÜNİVERSİTESİ", 
              alt.value(strings['bilkent_red']),
              alt.value(strings['bilkent_blue'])
            ),
            tooltip=[
              alt.Tooltip("uni:N", title=strings["uni"]),
              alt.Tooltip("aggregate_grad:Q", title=strings["grad"]),
              alt.Tooltip("frac:Q", title=strings["grad_per"], format=".0%"),
            ]
          ).properties(
            title=strings['top_uni_title'].format(num2show_uni),
          )
          text = uni_chart.mark_text(
            align='left',
            baseline='middle',
            dx=3  # Nudges text to right so it doesn't appear on top of the bar
          ).encode(
            text='aggregate_grad:Q',
            color=alt.value("white")
          )
          st.altair_chart((uni_chart + text), True)

          st.write(strings['spec_hs_info'])
          uni_selection = st.selectbox(strings['spec_uni_prompt'], pd.unique(data['uni'])) 
          merge = st.checkbox(strings['aggregated_checkbox'], value=True)
          if merge:
            base = alt.Chart(data).transform_filter(
              alt.datum.uni == uni_selection
            ).transform_aggregate(
              aggregate_grad='sum(total_grad)',
              groupby=['dept'],
            ).encode(
              theta=alt.Theta("aggregate_grad:Q", stack=True),
              radius=alt.Radius("aggregate_grad:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=70)),
              color=alt.Color("dept:N", legend=None),
              tooltip=[
                alt.Tooltip("dept:N", title=strings["dept"]),
                alt.Tooltip("aggregate_grad:Q", title=strings["grad"])
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
              if len(data.loc[(data['scho'] == scho) & (data['uni'] == uni_selection)]) != 0:
                base = alt.Chart(data).transform_filter(
                  (alt.datum.uni == uni_selection) & (alt.datum.scho == scho)
                ).transform_aggregate(
                  aggregate_grad='sum(total_grad)',
                  groupby=['dept'],
                ).encode(
                  theta=alt.Theta("aggregate_grad:Q", stack=True),
                  color=alt.Color("dept:N", legend=None),
                  tooltip=[
                    alt.Tooltip("dept:N", title=strings["dept"]),
                    alt.Tooltip("aggregate_grad:Q", title=strings["grad"])
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
            frac = alt.datum.aggregate_grad / ss.nums['hs']['grad']
          ).mark_bar().encode(
            x=alt.X('aggregate_grad:Q', aggregate='sum', title=strings["grad"]),
            y=alt.Y('dept:N',sort="-x", title=strings["dept"]),
            color=alt.value(strings['bilkent_blue']),
            tooltip=[
              alt.Tooltip("dept:N", title=strings["dept"]),
              alt.Tooltip("aggregate_grad:Q", title=strings["grad"]),
              alt.Tooltip("frac:Q", title=strings["grad_per"], format=".0%"),
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

          st.write(strings['spec_uni_info'])
          dept_selection = st.multiselect(strings['spec_dept_prompt'], pd.unique(data['dept'])) 
          if len(dept_selection) > 0:
            dept_merge = st.checkbox(strings['aggregated_checkbox'], value=True, key='dept_merge')
            if dept_merge:
              dept_base = alt.Chart(data).transform_filter(
                alt.FieldOneOfPredicate(field='dept', oneOf=dept_selection)
              ).transform_aggregate(
                aggregate_grad='sum(total_grad)',
                groupby=['uni'],
              ).encode(
                theta=alt.Theta("aggregate_grad:Q", stack=True),
                radius=alt.Radius("aggregate_grad:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=70)),
                color=alt.Color("uni:N", legend=None),
                tooltip=[
                  alt.Tooltip("uni:N", title=strings["uni"]),
                  alt.Tooltip("aggregate_grad:Q", title=strings["grad"])
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
                    groupby=['uni'],
                  ).encode(
                    theta=alt.Theta("aggregate_grad:Q", stack=True),
                    color=alt.Color("uni:N", legend=None),
                    tooltip=[
                      alt.Tooltip("uni:N", title=strings["uni"]),
                      alt.Tooltip("aggregate_grad:Q", title=strings["grad"])
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

      
        d = data.groupby("uni_city").agg({"total_grad": "sum"}).reset_index()
        d.loc[d['total_grad'] < ss['nums']['hs']['grad'] * 0.08, "uni_city"] = 'All Others'
        d = d.groupby("uni_city").agg({"total_grad": "sum"}).reset_index()
        d['dummy'] = 'City'
        city_chart = alt.Chart(d).transform_calculate(
          frac = alt.datum.total_grad / ss['nums']['hs']['grad']
        ).mark_bar().encode(
          x=alt.X('total_grad:Q', stack="normalize", title=None),
          row=alt.Row('dummy:N', title=None),
          color=alt.Color(
            'uni_city:N',
            legend=alt.Legend(
              orient='bottom',
              direction='horizontal',
            ),
            title=None
          ),
          tooltip=[
            alt.Tooltip("uni_city:N", title="City"),
            alt.Tooltip("total_grad:Q", title=strings["grad"]),
            alt.Tooltip("frac:Q", title=strings["grad_per"], format=".0%"),
          ]
        ).configure_axis(
          grid=False
        ).properties(title=strings['city_distribution'], height=100)
        st.altair_chart(city_chart, True)
    with table:
      st.dataframe(data)
