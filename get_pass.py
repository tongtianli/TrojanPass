import logging
import random
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from utils import get_image_name
from errors import *
from selenium.common.exceptions import TimeoutException


# Universal driver interface for Firefox or Chrome
class Driver:
    def __init__(self, firefox: bool = True, headless: bool = True):
        self.headless = headless

        if firefox:
            options = webdriver.FirefoxOptions()
            options.headless = headless
            self.driver = webdriver.Firefox(options=options)
        else:
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            self.driver = webdriver.Chrome(options=options)

    def __del__(self):
        logging.info('Finish job, driver quits.')
        self.driver.quit()

    def get(self, url: str):
        self.driver.get(url)

    def name(self) -> str:
        return self.driver.name

    def elem_by_xpath(self, xpath: str) -> WebElement:
        return self.driver.find_element_by_xpath(xpath)

    def elem_by_id(self, _id: str) -> WebElement:
        return self.driver.find_element_by_id(_id)

    def elem_by_name(self, name: str) -> WebElement:
        return self.driver.find_element_by_name(name)

    def elems_by_classname(self, class_name: str) -> List[WebElement]:
        return self.driver.find_elements_by_class_name(class_name)

    def elem_with_wait(self, approach: By, locator: str, time_limit: int = 10) -> WebElement:
        return WebDriverWait(self.driver, time_limit).until(
            expected_conditions.presence_of_element_located(
                (approach, locator))
        )

    def url(self):
        return str(self.driver.current_url)

    def current_url_ends(self, suffix: str) -> bool:
        return self.url().endswith(suffix)

    def delete_all_cookies(self):
        self.driver.delete_all_cookies()


class Passer:
    def __init__(self, net_id: str, net_pw: str, duo_code: int,
                 firefox: bool = True, headless: bool = True):
        self.net_id = net_id
        self.net_pw = net_pw
        self.duo_code = duo_code
        self.image_name = get_image_name(net_id)

        # recommend setting: Firefox headless or Chrome (without headless)
        self.driver = Driver(firefox, headless)

    def get_pass_and_reminder(self):
        try:
            logging.info(f"Attempt to run {self.driver.name()} with headless={self.driver.headless}")
            logging.info(f"Get pass for net_id: {self.net_id}.")

            self.login()

            if self.driver.elems_by_classname('btn-begin-assessment-disabled'):
                notification_text = self.driver.elems_by_classname('notification-message')[0].text
                raise SelfAssessmentNotCompliantError(f'Not able to start wellness assessment for {self.net_id}.',
                                                      notification_text)

            if self.driver.elems_by_classname('btn-begin-assessment'):
                self.self_assessment()

            logging.info("Done wellness assessment. Saving pass")

            if self.driver.current_url_ends('login'):
                logging.info('Re login required.')
                self.login(re_login=True)

            if self.driver.current_url_ends('dashboard'):
                pass_element = self.driver.elems_by_classname('day-pass-wrapper')[0]
                pass_element.screenshot(self.image_name)

                notification = self.driver.elems_by_classname('notification-message')[0].text
                logging.debug(f'{self.image_name} is saved and next_test_reminder is {notification}')

        except TimeoutException:
            random_image_name = f"error{random.randint(201, 500)}.png"
            self.driver.driver.save_screenshot(random_image_name)
            raise UnexpectedUrlError(f'Unexpected url before save pass for {self.net_id}', self.driver.url(),
                                     random_image_name)

    def login(self, re_login: bool = False):
        self.driver.get('https://trojancheck.usc.edu/login')

        if not re_login:
            # Click the login-with-netID button
            self.driver.elem_by_xpath('/html/body/app-root/app-login/main/section/div/div[1]/div[1]/button').click()

            # Input net ID and password
            self.driver.elem_with_wait(By.ID, "username").send_keys(self.net_id)
            self.driver.elem_by_id('password').send_keys(self.net_pw)

            # Login Button
            self.driver.elem_by_name('_eventId_proceed').click()

            if self.driver.elems_by_classname("form-error"):
                raise IncorrectPasswordError('Incorrect password', self.net_id)

            # try:
            #     self.driver.driver.switch_to.frame(self.driver.elem_with_wait(By.XPATH, '//iframe'))
            #     self.driver.elem_with_wait(By.ID, 'passcode').click()
            #     self.driver.elems_by_classname('passcode-input')[0].send_keys(self.duo_code)
            #     self.driver.elem_by_id('passcode').click()
            #     self.driver.driver.switch_to.default_content()
            # except Exception:
            #     pass

        # Continue button
        self.driver.elem_with_wait(By.CLASS_NAME, 'btn-next').click()


    def self_assessment(self):
        # prepare for begin_wellness_assessment
        self.driver.elem_with_wait(By.XPATH,
                                   '/html/body/app-root/app-dashboard/main/div/section[1]/div[2]/button').click()

        # start_screening
        self.driver.elem_with_wait(By.XPATH,
                                   '/html/body/app-root/app-assessment-start/main/section[1]/div[2]/button[2]').click()

        # select No
        # for i in range(2,):
        self.driver.elem_with_wait(By.XPATH, '//*[@id="mat-button-toggle-' + str(2) + '-button"]').click()

        self.driver.elems_by_classname('btn-next')[0].click()

        # select No
        for i in range(11, 24, 2):
            self.driver.elem_with_wait(By.XPATH, '//*[@id="mat-button-toggle-' + str(i) + '-button"]').click()

        self.driver.elems_by_classname('btn-next')[0].click()

        # finish assessment and wait loading page
        self.driver.elem_with_wait(By.XPATH, '//*[@id="mat-checkbox-1"]/label/div').click()

        self.driver.elems_by_classname('btn-submit')[0].click()

        # after assessment, back to home page
        self.driver.elem_with_wait(By.XPATH,
                                   '/html/body/app-root/app-assessment-confirmation/main/section[3]/a').click()
