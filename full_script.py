import os
from tqdm import tqdm
import requests
import re
import time
requests.packages.urllib3.disable_warnings() 
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

def get_all_results(cookies, step=1000):
    tqdm.write('getting all results')
    url = "https://nouveau-europresse-com.accesdistant.sorbonne-universite.fr/DocumentList/GetNextPage"

    params = {
        'listType': 1,
        'pageNo': 0,
        'docPerPage': step
    }
    res = requests.get('https://nouveau-europresse-com.accesdistant.sorbonne-universite.fr/DocumentList/GetNextPage', 
                       cookies=cookies, 
                       params=params, verify=False)
    return res.content.decode()

if __name__ == "__main__":
    # on prépare la regex de sélection des noms de documents
    reg = re.compile('checkbox-container selection-visible.*')

    # on créé le navigateur firefox
    profile = webdriver.FirefoxProfile()
    driver = webdriver.Firefox(profile)

    # on ouvre la page de connexion et on attend que l'utilisateur soit loggé, ait fait sa recherche, et ait trié par plus ancien
    driver.get('https://accesdistant.sorbonne-universite.fr/login?url=https://nouveau.europresse.com/access/ip/default.aspx?un=UPMCT_1')
    input("Appuyer sur entrée une fois la première recherche effectuée (penser à trier par plus ancien!!)")

    # on récupère le nombre total d'articles
    total_count = int(driver.find_element(By.CLASS_NAME, 'resultOperations-count').text.replace(' ', ''))

    current_count = 0
    all_parsed_documents = set()

    # on récupère les cookies de connexion
    all_cookies = driver.get_cookies()
    cookies = {}
    for cookie in all_cookies:
        cookies[cookie['name']] = cookie['value']

    # on procède par batchs tant qu'on a pas atteint le nombre total d'éléments
    with tqdm(total=total_count, position=0, leave=True) as pbar:
        while current_count < total_count:
            # TODO: REGARDER COMMENT REGLER LE PROBLEME DE DATE NON MODIFIEE ENTRE DEUX LOOPS
            
            # on récupère le résultat de la dernière recherche effectuée
            soup = bs(get_all_results(cookies), features="html.parser")
            prettyHTML = soup.prettify()

            # on récupère toutes les dates des articles
            all_dates = [el.contents[0].strip() for el in soup.find_all("span", {"class": "details"})]

            # on récupère tous les noms de documents
            all_documents = [el.get('name') for el in soup.find_all("div", {"class" : reg})]

            # on sauvegarde
            file_name = f'{all_dates[0]}_{all_dates[-1]}.html'
            tqdm.write(f"Downloading {file_name}")
            with open(os.path.join('output', file_name), 'w', encoding='utf-8') as f:
                f.write(prettyHTML)
            
            # on calcule le nombre de nouveaux documents récupérés (pour éviter le chevauchement entre date de fin précédente et date de début présente)
            nb_new_documents = len(set(all_documents) - all_parsed_documents)
            current_count += nb_new_documents
            pbar.update(nb_new_documents)

            # et on met à jour la liste des documents récupérés
            all_parsed_documents.update(all_documents)

            # on récupère les valeurs de la date la plus récente
            year, month, day = all_dates[-1].split('-')
            # et on supprime les 0 devant les mois et les jours
            month = str(int(month))
            day = str(int(day))

            # puis on repart sur la page de recherche
            driver.get('https://nouveau-europresse-com.accesdistant.sorbonne-universite.fr/Search/AdvancedMobile')

            # on récupère les éléments controlant la date de début
            select_day = Select(driver.find_element(By.XPATH, '/html/body/section/form/div/div[2]/div[1]/div[5]/div[3]/div/div[2]/span[1]/span/select[1]'))
            select_month = Select(driver.find_element(By.XPATH, '/html/body/section/form/div/div[2]/div[1]/div[5]/div[3]/div/div[2]/span[1]/span/select[2]'))
            select_year = Select(driver.find_element(By.XPATH, '/html/body/section/form/div/div[2]/div[1]/div[5]/div[3]/div/div[2]/span[1]/span/select[3]'))

            tqdm.write(f'Setting new values to search: day: {day}, month: {month}, year: {year}')
            
            # et on modifie les valeurs avec la nouvelle date à appliquer
            select_day.select_by_value(day)
            select_month.select_by_value(month)
            select_year.select_by_value(year)

            # puis on recommence
            btn = driver.find_element(By.ID, 'btnSearch')
            btn.click()

            time.sleep(1)