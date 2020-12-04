""" Scrapes the online Woolworth's catalogue for specials.
__author__ = Allan Chan
"""

from selenium import webdriver  # pip install selenium and webdriver_manager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import ctypes
import sys
import re


def element_selector(browser, mode, path, multiple=False, func=None):
    """ Searches and returns an element on a specified path.

    :params:
        - browser: webdriver for chrome
        - mode: 'css' or 'xpath' depending on the path format
        - path: path of the element
        - multiple:
            - True: returns a list of elements on the path
            - False: returns a single element on the path
        - func: performs a given function
    """
    loaded = False
    while not loaded:
        try:
            if mode == 'css':
                if multiple is False:
                    element_selected = browser.find_element_by_css_selector(path)
                elif multiple is True:
                    element_selected = browser.find_elements_by_css_selector(path)
            elif mode == 'xpath':
                if multiple is False:
                    element_selected = browser.find_element_by_xpath(path)
                elif multiple is True:
                    element_selected = browser.find_elements_by_xpath(path)
            if func is None:
                loaded = True
                return element_selected
            elif func(browser, mode, path):
                loaded = True
                return element_selected
        except Exception:
            pass


def link_of_last_woolworths(browser, mode, path):
    """ Returns the last good displayed on a page. This is used to ensure
    that pages have been fully loaded.

    :params:
        - browser: webdriver for chrome
        - mode: 'css' or 'xpath' depending on the path format
        - path: path of the element
    """
    all_elements = element_selector(browser, mode, path, multiple=True)
    last_element = all_elements[-1]
    link_of_last_element = last_element.find_element_by_xpath('.//shared-product-tile/section/div[1]/a')
    link_of_last = link_of_last_element.get_attribute('href')
    return link_of_last


if __name__ == "__main__":
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # uncomment if you want to see browser
    chrome_options.add_argument("--window-size=1024,768")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    browser = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    # read wishlist into hash table
    goods = {}
    with open("wishlist.txt") as f:
        lines = f.readlines()
        for item in lines:
            goods[str(item)] = True

    url = "https://www.woolworths.com.au/"
    total = 0
    browser.get(url)
    woolworths_hash = {}

    for good_iter in goods:
        # search for good
        search_field = element_selector(browser, 'css', '#headerSearch')
        search_field.clear()
        search_field.send_keys(good_iter)
        search_button = element_selector(browser, 'css', '#header-panel > shared-header > shared-core-header > header > shared-header-search > form > div > div > div.autocomplete-actionButtonWrapper > button.autocomplete-actionButton.autocomplete-searchButton')
        search_button.click()

        # waits for specials button to load
        def filter_specials(browser, mode, path):
            element = element_selector(browser, mode, path)
            element_text = element.text
            bracket_regex = re.findall(r'\(', element_text)
            if len(bracket_regex) > 0:
                return True
            else:
                return False

        # filter by specials if there are specials
        special_button = element_selector(browser, 'xpath', '//*[@id="content-container"]/div/shared-side-bar-navigation/div/nav/shared-navigation-item[3]/a', func=filter_specials)
        link_enabled = special_button.get_attribute('class')
        classes = link_enabled.split()
        if 'is-disabled' not in classes:
            link_last_element_old = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-grid > div > div', multiple=True, func=link_of_last_woolworths)
            browser.get(special_button.get_attribute('href'))

        # check if we need to wait for page to update
        product_count_element = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > div > wow-record-count > div')
        product_count = re.findall(r'\d+', product_count_element.text)
        if len(product_count) == 1:
            skip_wait = True
        else:
            skip_wait = False

        # ensure filtered specials page has loaded
        if not skip_wait:
            def wait_for_page(browser, mode, path):
                link_last_element_new = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-grid > div > div', multiple=True, func=link_of_last_woolworths)
                if link_last_element_new != link_last_element_old:
                    return True
            element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-grid > div > div', func=wait_for_page)

        # get page count
        product_count_element = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > div > wow-record-count > div')
        product_count = re.findall(r'\d+', product_count_element.text)
        if len(product_count) > 1 and product_count[1] != product_count[2]:
            page_total_element = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-paging > div > div.page-indicator')
            page_total = re.findall(r'(\d+)$', page_total_element.text)
            page_total = int(page_total[-1])
        else:
            page_total = 1

        specials = {}
        link_last_element_old = ''
        # go through each page of specials
        for page in range(page_total):

            # wait for page to update if there's more than 1 page
            if page_total > 1:
                element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-grid > div > div', func=wait_for_page)

            # calculate and filter discounts for each item displayed
            all_elements = element_selector(browser, 'css', 'shared-product-tile > section > div.shelfProductTile-content > div > div > shared-price > div.price-was.price--large.ng-star-inserted', multiple=True)
            for item in all_elements:
                try:
                    # get current price
                    parent = item.find_element_by_xpath('..')
                    child_dollar = parent.find_element_by_xpath('.//div[1]/span[2]')
                    child_cents = parent.find_element_by_xpath('.//div[1]/div/span[2]')
                    current_price = float((100 * int(child_dollar.text) + int(child_cents.text))/100)

                    # get old price
                    old_price = item.text
                    old_price = re.findall(r'\$(.*)$', old_price)

                    # get name of product
                    name = parent.find_element_by_xpath('..')
                    name2 = name.find_element_by_xpath('..')
                    heading = name2.find_element_by_xpath('.//span')

                    # include if the discount is greater than 25%
                    if 1 - current_price / float(old_price[0]) > 0.25:
                        specials[heading.text] = (current_price, 1 - current_price / float(old_price[0]))
                except Exception as e:
                    print(e)

            # go to next page if it exists
            if page < int(page_total) - 1:
                next_page = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-paging > div > div.paging-section > a.paging-next.ng-star-inserted')
                link_last_element_old = element_selector(browser, 'css', '#search-content > div > wow-product-search-container > shared-grid > div > div', multiple=True, func=link_of_last_woolworths)
                print(f"page {page + 1} done")
                browser.get(next_page.get_attribute('href'))

        good_query = good_iter.rstrip('\n')
        woolworths_hash[good_query] = specials  # add the specials for this good to the discounts hash table
        print(f'\'{good_query}\' completed')

    # write all discounts to a file
    with open("specials.txt", "r+") as f:
        f.truncate(0)
        f.seek(0)
        for key in woolworths_hash:
            for inner_key in woolworths_hash[key]:
                f.write(f'{inner_key}  - ${"%.2f" % round(woolworths_hash[key][inner_key][0], 2)} - {"%.2f" % round(woolworths_hash[key][inner_key][1] * 100, 2)}% \n')
                total += 1
        f.truncate()

    ctypes.windll.user32.MessageBoxW(0, f"There are {total} specials!", "Specials tracker!", 1)
    browser.quit()
    sys.exit()
