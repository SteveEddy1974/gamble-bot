#!/usr/bin/env python3
"""Dump full live DOM HTML from the current Chrome tab (remote debug 9222)."""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By


def main():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    driver = webdriver.Chrome(options=chrome_options)
    print(f"Connected to: {driver.title}")

    # Give the page a moment to finish any dynamic updates
    time.sleep(1.5)

    # Capture the live DOM (includes dynamic content)
    html = driver.execute_script("return document.documentElement.outerHTML;")

    output_file = "page_dom.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Saved live DOM to: {output_file}")


if __name__ == "__main__":
    main()
