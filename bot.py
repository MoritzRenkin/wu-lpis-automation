import selenium.common.exceptions as selenium_exceptions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
from datetime import datetime, timedelta
from configparser import ConfigParser
import pause
import sys
from drivers.drivers import start_chromedriver, start_geckodriver
from threading import Thread
import requests
import logging
import os


if getattr(sys, 'frozen', False):
    file_path = os.path.dirname(sys.executable)
elif __file__:
    file_path = os.path.dirname(__file__)
else:
    file_path = None


class Bot:
    def __init__(self, username, password, tasks, browser, driver_status, headless, time_manager, exit_event):

        self.username = username
        self.pw = password
        self.status = driver_status
        self.browser = browser
        self.headless = headless
        self.time_manager = time_manager
        self.exit_event = exit_event
        self.tasks = tasks

        self.driver = None

    def __call__(self):

        self.run()


    def pull_config(self):
        parser = ConfigParser()
        try:
            parser.read(os.path.join(file_path, "config.ini"))
            self.config = parser["bot"]

        except Exception as e:
            self.status.value = b'Config file corrupted or missing'
            raise e

        logging.basicConfig(filename=os.path.join(file_path, 'debug_logs.log'),
                            format='%(asctime)s - %(module)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('LPIS')
        self.logger.setLevel(int(self.config['log_level']))

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(int(self.config['log_level']))
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.debug(f'Browser: {self.browser}')

    def run(self):
        Thread(target=self.check_exit_event, daemon=True).start()

        try:
            self.pull_config()

            self.status.value = b'Checking for driver updates'
            self.prepare_drivers()

            def sorter(a):
                if str(a[0]) == 'now':
                    return datetime.min
                else:
                    return a[0]

            for submit_time, lv_tuples in sorted(self.tasks.items(), key=sorter):
                if self.driver is not None:
                    self.driver.quit()

                self.await_task(submit_time)

                self.status.value = b'Starting up'
                self.start_driver()

                self.status.value = b'Logging in'
                self.login()

                self.subscribe_courses(lv_tuples, submit_time)

        except WuError as e:
            self.logger.warning(f"WuError: {e.msg}")
            self.status.value = str(e).replace('ä', 'ae').replace('ü', 'ue').replace('ö', 'oe').encode('UTF-8')

        except selenium_exceptions.WebDriverException:
            self.logger.exception("Webdriver Error:")
            # message = str(e).lstrip('Message: ').rstrip('\n')
            self.status.value = b'Driver Error'

        except Exception as e:
            self.logger.critical("Unhandled Exception")
            self.logger.exception('')
            self.status.value = b'Unspecified Error'

        finally:
            try:
                self.logger.debug("Finished with run, quitting webdriver and exiting after 4 seconds")
            except AttributeError:
                pass

            time.sleep(4)

            try:
                self.driver.quit()
                self.driver = None
                self.logger.warning('---------------- Exiting ----------------')

            except (AttributeError, selenium_exceptions.InvalidSessionIdException):
                pass


            sys.exit()

    def start_driver(self, headless=None, update=False):
        if not headless:
            headless = self.headless
        if self.browser == 'Google Chrome':
            self.driver = start_chromedriver(headless=headless, update=update)

        elif self.browser == 'Firefox':
            self.driver = start_geckodriver(headless=headless)

        else:
            raise RuntimeError('Browser not known')

    def login(self):
        self.driver.implicitly_wait(2)
        self.driver.get('https://lpis.wu.ac.at/lpis')

        username_field = self.driver.find_element_by_xpath('/html/body/form/table/tbody/tr[1]/td[2]/input')
        username_field.send_keys(self.username)

        password_field = self.driver.find_element_by_xpath('/html/body/form/table/tbody/tr[2]/td[2]/input')
        password_field.send_keys(self.pw)

        submit_button = self.driver.find_element_by_xpath('/html/body/form/input[1]')
        submit_button.click()

        check_error_xpath(self.driver, '/html/body/div/h3/span')

    def subscribe_courses(self, courses, submit_time):
        self.logger.info(f'subscribing {courses}')

        for subject_area, lv_id in courses:
            subject_binary = subject_area[:20].encode('UTF-8')

            self.logger.info(f'Registering to {subject_area}')
            self.status.value = b'Registering to ' + subject_binary

            select = Select(self.driver.find_element_by_xpath('/html/body/form/select'))
            select.select_by_index(0)
            anzeigen_button = self.driver.find_element_by_xpath('/html/body/form/input[4]')
            anzeigen_button.click()
            try:
               # subject_link = self.driver.find_element_by_link_text(subject_area)
                subject_link = self.find_subject_link(subject_area)
                subject_link.click()
            except selenium_exceptions.NoSuchElementException:
                self.logger.warning(f'No Subject Area found named {subject_area}, assuming invalid Subject Area')
                self.status.value = b'Invalid Subject: ' + subject_binary
                continue

            if submit_time != 'now' and submit_time > self.time_manager.corrected_now():
                self.logger.info('Performing Ping Tests in anticipation for countdown')
                self.status.value = b'Performing Ping Tests'
                ping = self.ping_test(int(self.config['ping_tests']))
                submit_time = submit_time - timedelta(seconds=ping + float(self.config['ping_safety_margin']))
                self.logger.info(f'Mean ping: {ping}, refresh time: {submit_time}. Entering Countdown')
                self.status.value = b'Countdown for subject ' + subject_binary + b'\n Refreshing at ' + str(submit_time.time()).encode('UTF-8')
                corrected_submit_time = self.time_manager.get_local(submit_time)
                pause.until(corrected_submit_time)

            refresh_attempts = int(self.config['refresh_attempts'])
            refresh_interval = float(self.config['refresh_interval'])
            for i in range(0, refresh_attempts):
                self.logger.info('Refreshing...')
                self.driver.refresh()
                table = self.driver.find_element_by_class_name('b3k-data').find_element_by_tag_name('tbody')
                rows_list = table.find_elements_by_tag_name('tr')
                anmelden_button = None
                for row in rows_list:
                    row_id = row.find_element_by_tag_name('a').get_attribute('innerHTML')
                    if row_id == lv_id:
                        anmelden_button = row.find_elements_by_tag_name('input')[-1]
                        break

                if anmelden_button is None:
                    self.logger.info(f'Could not find Register Button for Course ID {lv_id}, assuming invalid')
                    self.status.value = b"Invalid Course ID: " + str(lv_id).encode('UTF-8')
                    break

                if anmelden_button.get_attribute('disabled') != 'true':
                    self.logger.info('Enabled Registration Button found, submitting')
                    anmelden_button.click()
                    try:
                        success_msg = self.driver.find_element_by_xpath('/html/body/div/div/b').get_attribute('innerHTML')
                    except selenium_exceptions.NoSuchElementException:
                        self.logger.exception('Registration unsuccessful: ')
                        success_msg = 'Registration was unsuccessful'

                    self.status.value = success_msg.replace('ü', 'ue').encode('UTF-8')

                    break

                elif i == refresh_attempts - 1:
                    self.status.value = b'Registration is not yet allowed'

                time.sleep(refresh_interval)

            '''
            self.driver.find_element_by_xpath('/html/body/a[7]').click()
            lv_input = self.driver.find_element_by_xpath('/html/body/form/input[2]')
            lv_input.send_keys(lv_id)

            submit_button = self.driver.find_element_by_xpath('/html/body/form/input[5]')
            print(f'Pausing until {submit_time}')
            if submit_time != 'now':
                pause.until(submit_time)

            submit_button.click()

            try:
                check_error_xpath(self.driver, '/html/body/div/div/b')
            except WuError:
                print("Invalid Course ID")
                self.status.value = b'Invalid Course ID: ' + str(lv_id).encode('UTF-8')
                continue

            errors = []
            spans = self.driver.find_elements_by_tag_name('span')
            if len(spans):
                for span in spans:
                    if 'font-weight: bold; color: red;' in str(span.get_attribute('style')):
                        errors.append(span.get_attribute('innerHTML'))
                raise WuError('\n'.join(errors))

            self.status.value = b'Registered course ' + str(lv_id).encode('UTF-8')
        '''
    def find_subject_link(self, subject_area):
        split = subject_area.split(' ')
        subject_type = split[0]
        subject_area = ' '.join(split[1:]).replace('&', '&amp;')
        self.logger.info(f"Looking for {subject_area} | {subject_type}")

        table = self.driver.find_element_by_class_name('b3k-data').find_element_by_tag_name('tbody')
        for row in table.find_elements_by_tag_name('tr'):
            try:
                spans_in_td = row.find_element_by_tag_name('td').find_elements_by_tag_name('span')
                lv_type = spans_in_td[0].get_attribute('innerHTML')
                lv_name = spans_in_td[1].get_attribute('innerHTML')

                self.logger.debug(f"Iteration at: {lv_name} | {lv_type}")
                if subject_area == lv_name and subject_type == lv_type:
                    subject_link = spans_in_td[2].find_element_by_tag_name('a')
                    return subject_link

            except IndexError:
                continue
        raise selenium_exceptions.NoSuchElementException('Thrown because no matching subject area was found.')

    def ping_test(self, amount):
        if amount == 0:
            return 0

        results = []
        for _ in range(amount):
            time_before = time.time()
            self.driver.refresh()
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '/html/body/table[2]/tbody')
                )
            )
            # just a test if element is really visible:
            self.driver.find_element_by_xpath('/html/body/table[2]/tbody').get_attribute('innerHTML')

            time_after = time.time()
            results.append(time_after - time_before)
            time.sleep(3)

        self.logger.debug(f'Ping test results were {results}')
        return sum(results) / amount

    def await_task(self, submit_time):
        if submit_time != 'now':
            wakeup = submit_time - timedelta(minutes=float(self.config['minutes_before_start']))
            corrected_wakeup = self.time_manager.get_local(wakeup)
            if corrected_wakeup > datetime.now():
                self.logger.info(f'Awaiting task, wakeup at {wakeup}')
                self.status.value = b'Waiting until ' + wakeup.strftime("%H:%M:%S.%f").rstrip('0').encode('UTF-8')
                pause.until(corrected_wakeup)

        else:
            self.logger.debug('Skipping await_task because submit_time is now')

    def prepare_drivers(self):
        try:
            self.logger.debug("Checking Internet Connection")
            requests.get('https://www.wu.ac.at/')
        except requests.exceptions.ConnectionError:
            raise WuError('No Internet Connection')

        try:
            self.logger.info('Checking for driver updates')
            self.start_driver(headless=True)
        except (selenium_exceptions.SessionNotCreatedException, IndexError, OSError):
            self.logger.info('Starting with current installed driver failed. Attempting update')
            self.status.value = b'Updating drivers'
            self.start_driver(update=True, headless=True)
            self.logger.info('Update finished')
        
        finally:
            self.driver.quit()
            self.driver = None


    def check_exit_event(self):
        while True:
            if self.exit_event.is_set():
                if self.driver is not None:
                    self.driver.quit()
                return
            time.sleep(0.1)


def check_existence_by_id(driver, id):
    try:
        driver.find_element_by_id(id)
    except selenium_exceptions.NoSuchElementException:
        return False
    return True



def check_error_xpath(driver, xpath):
    try:
        elem = driver.find_element_by_xpath(xpath)
        return check_error_field(elem)
    except selenium_exceptions.NoSuchElementException:
        return False


def check_error_field(elem):
    msg = elem.get_attribute('innerHTML')
    raise WuError(msg)


class WuError(Exception):
    def __init__(self, message):
        self.msg = message
        super().__init__(message)
