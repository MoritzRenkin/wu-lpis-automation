import os
from selenium import webdriver
import selenium.common.exceptions as selenium_exceptions
import sys

if getattr(sys, 'frozen', False):
    driver_dir = os.path.join(os.path.dirname(sys.executable), 'drivers')
elif __file__:
    driver_dir = os.path.dirname(__file__)


def start_geckodriver(headless):
    options = webdriver.firefox.options.Options()
    webdriver.firefox
    if headless:
        options.headless = True
    executable = os.path.join(driver_dir, 'geckodriver.exe')
    driver = webdriver.Firefox(executable_path=executable, options=options)
    return driver


def start_chromedriver(headless, update=False):
    service_args = ["hide_console", ]
    options = webdriver.ChromeOptions()
    options.add_argument('log-level=OFF')
    if headless:
        options.add_argument('--headless')

    chromedriver_dir = os.path.join(driver_dir, 'chromedrivers')
    if update:
        update_chromedriver()

        executables = [os.path.join(chromedriver_dir, f) for f in os.listdir(chromedriver_dir)]
        for current in executables:
            try:
                driver = webdriver.Chrome(executable_path=current, options=options, service_args=service_args)
                executables.remove(current)
                for current in executables:
                    os.remove(current)
                break
            except (selenium_exceptions.SessionNotCreatedException, OSError):
                continue

        if driver is None:
            raise selenium_exceptions.SessionNotCreatedException('All chromedriver versions raised exceptions')

    else:
        files = os.listdir(chromedriver_dir)
        if len(files) is not 1:
            raise IndexError('Called start_chromedriver with invalid number of available executables')
        executable = os.path.join(chromedriver_dir, files[0])
        driver = webdriver.Chrome(executable_path=executable, options=options, service_args=service_args)

    return driver


def update_chromedriver():
    from bs4 import BeautifulSoup
    import requests
    import urllib
    import zipfile

    PLATFORMS = {'darwin': 'mac64', 'win32': 'win32', 'linux': 'linux62', 'linux2': 'linux62'}
    DOWNLOAD_DIR = './drivers/chromedrivers/'

    CHROMEDRIVER_URL = 'https://chromedriver.storage.googleapis.com/'
    CHROMEDRIVER_FILE_NAME = 'chromedriver_'
    CHROMEDRIVER_EXTENSION = '.zip'

    #deleting old files
    old_files = [f for f in os.listdir(DOWNLOAD_DIR) if os.path.isfile(os.path.join(DOWNLOAD_DIR, f))]
    for file in old_files:
        os.remove(os.path.join(DOWNLOAD_DIR, file))

    r = requests.get('https://chromedriver.chromium.org/downloads')
    doc = BeautifulSoup(r.text, 'html.parser')
    table = doc.find_all('table', {'class':['sites-layout-name-one-column', 'sites-layout-hbox']})[2]
    div = table.find('div').find('div')
    a_elements = div.find_all('a')

    versions = []
    for a in a_elements[:3]:
        original = (a['href'])
        version = original.split('=')[1][:-1]
        versions.append(version)

    for version in versions:
        p = PLATFORMS[sys.platform]
        filename = CHROMEDRIVER_FILE_NAME + p
        filename_version = version + '/' + filename + CHROMEDRIVER_EXTENSION
        url = CHROMEDRIVER_URL + filename_version
        print(url)

        try:
            file = urllib.request.urlopen(url)
        except:
            continue

        # save file to system
        path = os.path.join(DOWNLOAD_DIR, filename + CHROMEDRIVER_EXTENSION)
        with open(path, 'wb') as output:
            output.write(file.read())

        # unzip file
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(DOWNLOAD_DIR)

        # rename file
        extracted_name = 'chromedriver'
        filename += '_' + version
        if p == 'win32':
            extracted_name += '.exe'
            filename += '.exe'

        final_path = os.path.join(DOWNLOAD_DIR, filename)

        os.rename(os.path.join(DOWNLOAD_DIR, extracted_name), final_path)

        # give execute permission
        os.chmod(final_path, 0o755)

        # delete zip file
        os.remove(path)
