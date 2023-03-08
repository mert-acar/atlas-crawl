import json
import random
import pandas as pd
from time import sleep
from io import BytesIO  
import streamlit as st
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib3.exceptions import MaxRetryError
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains as AC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def button_callback():
  st.session_state.start = True

def download_ready(data):
  output = BytesIO()
  writer = pd.ExcelWriter(output, engine='openpyxl')
  data.to_excel(writer, index=False, sheet_name='data')
  writer.save()
  processed_data = output.getvalue()
  return processed_data

def checkPopUp():
  AC(driver).click().perform()
  sleep(0.5)
  AC(driver).click().perform()

if __name__ == "__main__":
  st.set_page_config(layout="wide", page_title="BTO - AtlasCrawl")
  try:
    strings = st.session_state['strings']
  except KeyError:
    with open("data/strings.json", "r") as f:
      strings = json.load(f)

  st.write(strings['title'])
  strings = strings['NewData']
  st.write(strings['page_title'])
  st.markdown(strings['message'])

  unis = pd.read_excel("data/unis.xlsx", engine='openpyxl')
  unique_unis = unis['UNI']
  selected_unis = unique_unis

  all_unis_selected = st.selectbox(
    strings['select_box']['prompt'],
    [
      strings['select_box']['choice_all'],
      strings['select_box']['choice_select']
    ]
  )
  if all_unis_selected == strings['select_box']['choice_select']:
    selected_unis = st.multiselect(
      strings['multi_select'],
      unique_unis,
      default=[]
    )

  unis = unis[unis['UNI'].isin(selected_unis)]
  if "start" not in st.session_state:
    st.session_state["start"] = False
  if "master_data" not in st.session_state:
    st.session_state['master_data'] = pd.DataFrame()

  start_button = st.button(strings['start_button'], on_click=button_callback)
  if start_button:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    master_data = {
      'hs': [],
      'hs_city': [],
      'hs_district': [],
      'uni': [],
      'uni_city': [],
      'fac': [],
      'dept': [],
      'scho': [],
      'new_grad': [],
      'old_grad': [],
      'total_grad': []
    }

    URL = "https://yokatlas.yok.gov.tr/lisans-univ.php?u="
    TABLE = {
      'link': '//*[@id="h1060"]/a/h4',
      'waitCondition': '//*[@id="icerik_1060"]/table/thead/tr[2]/th[2]'
    }
    PATIENCE = 5

    uni_text = st.empty()
    upbar = st.progress(0) 
    pbar = st.progress(0) 
    status_text = st.empty()
    for j in range(len(unis)):
      line = unis.iloc[j]
      uni = line["UNI"]
      idx = line["UNI_ID"]
      uni_text.text(uni + "  [{}/{}]".format(j + 1, len(unis)))
      upbar.progress((j + 1) / len(unis))

      # Go to university page
      sleep(random.randint(1,4))
      driver.get(URL + str(idx))

      # Get all the links from the page
      depts = driver.find_elements(By.XPATH, "//a[@href]")

      # Filter only the department links
      depts = list(filter(lambda x: 'lisans.php?y=' in x, map(lambda x: x.get_attribute("href"), depts)))
      total_dept = len(depts)

      # Loop through departments
      for i in range(total_dept):
        dept = depts[i]

        # Go to department page
        driver.get(dept)

        # Wait for the page to load
        try:
          WebDriverWait(driver, PATIENCE).until(EC.presence_of_element_located((By.XPATH, TABLE['link'])))
        except TimeoutException:
          continue

        checkPopUp()
        # Get the name of the deparment from the page
        dept_name = driver.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[3]/div/h2').text.split('-')[-1].strip()
        p = (i + 1) / total_dept
        pbar.progress(p)
        status_text.text("{} Complete\t[{}/{}]".format(dept_name, i + 1, total_dept))

        # Click to expand the table
        handle = driver.find_element(By.XPATH, TABLE['link'])
        handle.click()

        faculty = driver.find_element(By.XPATH, '/html/body/div[2]/div[1]/div[2]/div/h3[1]').text.split(':')[-1].strip()
        try:
          # Wait for the table to load
          WebDriverWait(driver, PATIENCE).until(EC.presence_of_element_located((By.XPATH, TABLE['waitCondition'])))
          try:
            table = pd.read_html(driver.page_source)[0].replace('---', 0).drop(0, axis=0)
          except KeyError:
            continue
          table.columns = table.columns.droplevel()
          for _, row in table.iterrows():
            hs = row['Lise']
            idxx = hs[::-1].find("(")
            if idxx == -1:
              continue
            location = hs[len(hs) - idxx: -1]
            pure_name = hs[:len(hs) - idxx - 1].strip()
            location = location.split(" - ")
            master_data['hs_city'].append(location[0])
            if len(location) > 1:
              master_data['hs_district'].append(location[1])
            master_data['hs'].append(pure_name)
            master_data['uni'].append(uni)
            master_data['uni_city'].append(unis.loc[unis['UNI'] == uni, 'CITY'].item())
            master_data['fac'].append(faculty)
            master_data['new_grad'].append(int(row["Lise'den Yeni Mezun"]))
            master_data['old_grad'].append(int(row["Önceki Mezun"]))
            master_data['total_grad'].append(int(row["Toplam"]))
            if 'Ücretli' in dept_name:
              master_data['scho'].append(0)
              dept_name_s = dept_name.replace(' (Ücretli)', '')
            elif '%' in dept_name:
              burs = dept_name[-13:-11]
              master_data['scho'].append(int(burs))
              dept_name_s = dept_name.replace(' (%' + burs + ' İndirimli)', '')
            elif 'Burslu' in dept_name:
              master_data['scho'].append(100)
              dept_name_s = dept_name.replace(' (Burslu)', '')
            else:
              master_data['scho'].append(-1)
              dept_name_s = dept_name
            master_data['dept'].append(dept_name_s)

        except TimeoutException:
          break

      pbar.empty()
      status_text.empty()
    master_data = pd.DataFrame(master_data)
    master_data.loc[master_data['hs'] == "AÇIK ÖĞRETİM LİSESİ", "hs_city"] = "AÇIK ÖĞRETİM LİSESİ"
    st.session_state.master_data = master_data
    driver.quit()

  if st.session_state.start:
    col1, col2 = st.columns([.2, .8])
    now = datetime.now().strftime("%d-%m-%Y-%H-%M")
    with col1:
      st.download_button(
        label=strings['download_button'],
        data=download_ready(st.session_state.master_data),
        file_name='liseler-' + now + '.xlsx'
      )

    with col2:
      save = st.button(strings['save_button'])
      if save:
        st.session_state.master_data.to_parquet("data/crawls/crawl-" + now + ".pq")
        st.success("Saved to server!")
