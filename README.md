# Woolworth's scraper
Scrapes the online woolworth's website for any specials!

Usage:
1. Add the products that you want to search for in the text file wishlist.txt separated line by line
2. Ensure selenium and webdriver_manager packages are installed
  - You can install them with the following commands:
    - pip install selenium
    - pip install webdriver_manager
3. Run catalogue_scraper.py
  - Settings:
    - Hide browser: Uncomment line 66 'chrome_options.add_argument("--headless")'
    - Change discount: Change line 168 to the desired discount percentage
4. All specified discounts are saved in the text file specials.txt
