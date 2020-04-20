import logging
import os
import platform
import random
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep


class WholeFoodsDeliverySlot:
    def __init__(
        self,
        ifttt_webhook_name,
        ifttt_webhook_key,
        speak=True,
        min_wait=2,
        max_wait=299,
        amazon_smile=True,
        firefox_driver_path="/usr/local/bin/geckodriver",
    ):
        self.ifttt_webhook_name = ifttt_webhook_name
        self.ifttt_webhook_key = ifttt_webhook_key
        self.min_wait = min_wait
        self.max_wait = max_wait
        if amazon_smile:
            self.amazon_subdomain = "smile"
        else:
            self.amazon_subdomain = "www"
        self.cart_url = f"https://{self.amazon_subdomain}.amazon.com/gp/cart/view.html?ref_=nav_cart"
        self.driver = webdriver.Firefox(executable_path=firefox_driver_path)
        self.speak = speak

    def main(self):
        self._setup()
        while True:
            output = self._discover_slot()
            if output:
                self._alert(output)
                break
            else:
                self._random_wait()

    def _setup(self):
        self.driver.get(f"https://{self.amazon_subdomain}.amazon.com")
        input("Sign in to Amazon, then press return to continue...")
        self.driver.get(self.cart_url)
        input(
            "Navigate to Whole Foods 'Schedule your order' page, then press return to continue..."
        )

    def _random_wait(self):
        wait_time = random.randrange(self.min_wait, self.max_wait)
        print("Waiting to refresh...", end="", flush=True)
        for s in range(wait_time, 0, -1):
            print(f"{s}...", end="", flush=True)
            sleep(1)
        print("0...\n")

    def _alert(self, message):
        print(message)
        if platform.system() == "Darwin" and self.speak:
            # Verbal notification on mac
            os.system(f'say "{message}"')
        # value1 is message, value 2 is URL
        requests.post(
            f"https://maker.ifttt.com/trigger/{self.ifttt_webhook_name}/with/key/{self.ifttt_webhook_key}",
            data={"value1": str(message), "value2": str(self.cart_url)},
        )

    def _discover_slot(self):
        """ Refreshes 'Schedule your order' page and looks for slots"""

        self.driver.refresh()
        print("Refreshed.")
        html = self.driver.page_source
        soup = BeautifulSoup(html, features="html.parser")

        slot_patterns = [
            "Next available",
            "1-hour delivery windows",
            "2-hour delivery windows",
        ]
        try:
            next_slot_text = soup.find(
                "h4", class_="ufss-slotgroup-heading-text a-text-normal"
            ).text
            if any(next_slot_text in slot_pattern for slot_pattern in slot_patterns):
                return "SLOTS OPEN!"
        except AttributeError:
            pass

        try:
            slot_opened_text = "Not available"
            all_dates = soup.findAll(
                "div", {"class": "ufss-date-select-toggle-text-availability"}
            )
            for each_date in all_dates:
                if slot_opened_text not in each_date.text:
                    return "SLOTS OPEN!"
        except AttributeError:
            pass

        try:
            no_slot_pattern = "No delivery windows available. New windows are released throughout the day."
            if no_slot_pattern == soup.find("h4", class_="a-alert-heading").text:
                print("NO SLOTS!")
        except AttributeError:
            return "Script Error, but a slot may be open."
