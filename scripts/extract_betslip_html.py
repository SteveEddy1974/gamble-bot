#!/usr/bin/env python3
"""Extract bet slip HTML structure for analysis."""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def main():
    print("Connecting to Chrome (remote debugging port 9222)...")
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    driver = webdriver.Chrome(options=chrome_options)
    print(f"✓ Connected to: {driver.title}")
    
    # Wait for side bets to be available
    print("\nWaiting for side bets to appear...")
    time.sleep(2)
    
    # Click on Side bets market tab
    try:
        side_bets_tab = driver.find_element(By.XPATH, "//*[contains(text(),'Side bets market')]")
        driver.execute_script("arguments[0].click();", side_bets_tab)
        print("✓ Clicked Side bets market tab")
        time.sleep(1)
    except:
        print("⚠️  Could not find Side bets tab (might already be selected)")
    
    # Find any clickable bet cell
    print("\nLooking for bet cells...")
    cells = driver.find_elements(By.XPATH, 
        "//tr[contains(@class,'market-view-row')]//td[contains(@class,'cell-table')][.//span[contains(@class,'cell-odds')]]")
    
    visible_cells = [c for c in cells if c.is_displayed()]
    print(f"Found {len(visible_cells)} visible bet cells")
    
    if not visible_cells:
        print("❌ No bet cells found. Make sure:")
        print("   - You're on the Exchange Baccarat page")
        print("   - A new round has started (betting is open)")
        print("   - Side bets are visible")
        driver.quit()
        return
    
    # Click the first available cell
    print(f"\nClicking first available bet cell...")
    target_cell = visible_cells[0]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_cell)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", target_cell)
    print("✓ Clicked bet cell")
    
    # Wait for bet slip to appear
    print("\nWaiting for bet slip to appear...")
    time.sleep(3)
    
    # Try to find bet slip container
    bet_slip_selectors = [
        "//div[contains(@class,'xgame-betslip')]",
        "//div[contains(@class,'betslip')]",
        "//div[contains(@class,'bet-slip')]",
        "//div[contains(@class,'verify-bets')]",
        "//div[contains(@class,'place-bets')]"
    ]
    
    bet_slip = None
    for selector in bet_slip_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for elem in elements:
                if elem.is_displayed():
                    bet_slip = elem
                    print(f"✓ Found bet slip using selector: {selector}")
                    break
            if bet_slip:
                break
        except:
            continue
    
    if not bet_slip:
        print("❌ Could not find bet slip container")
        print("\nSearching for any visible input fields...")
        inputs = driver.find_elements(By.XPATH, "//input[@type='number' or @type='text']")
        visible_inputs = [inp for inp in inputs if inp.is_displayed()]
        if visible_inputs:
            print(f"Found {len(visible_inputs)} visible inputs:")
            for inp in visible_inputs:
                print(f"  - name='{inp.get_attribute('name')}' placeholder='{inp.get_attribute('placeholder')}'")
                print(f"    HTML: {inp.get_attribute('outerHTML')[:200]}")
        driver.quit()
        return
    
    # Extract HTML
    print("\n" + "="*80)
    print("BET SLIP HTML:")
    print("="*80)
    html = bet_slip.get_attribute('outerHTML')
    print(html)
    print("="*80)
    
    # Also save to file
    output_file = "betslip_html.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n✓ HTML saved to: {output_file}")
    
    # Extract specific elements
    print("\n" + "="*80)
    print("SPECIFIC ELEMENTS:")
    print("="*80)
    
    # Find stake input
    print("\n1. STAKE INPUT FIELDS:")
    stake_inputs = bet_slip.find_elements(By.XPATH, ".//input[@type='number' or @type='text' or contains(@name,'stake') or contains(@placeholder,'stake')]")
    for idx, inp in enumerate(stake_inputs):
        if inp.is_displayed():
            print(f"   Input {idx + 1}:")
            print(f"   - name: {inp.get_attribute('name')}")
            print(f"   - placeholder: {inp.get_attribute('placeholder')}")
            print(f"   - class: {inp.get_attribute('class')}")
            print(f"   - HTML: {inp.get_attribute('outerHTML')}")
            print()
    
    # Find radio buttons
    print("2. RADIO BUTTONS:")
    radios = bet_slip.find_elements(By.XPATH, ".//input[@type='radio']")
    for idx, radio in enumerate(radios):
        if radio.is_displayed() or True:  # Check all radios
            print(f"   Radio {idx + 1}:")
            print(f"   - name: {radio.get_attribute('name')}")
            print(f"   - value: {radio.get_attribute('value')}")
            print(f"   - checked: {radio.is_selected()}")
            print(f"   - HTML: {radio.get_attribute('outerHTML')}")
            print()
    
    # Find buttons
    print("3. BUTTONS:")
    buttons = bet_slip.find_elements(By.XPATH, ".//button")
    for idx, btn in enumerate(buttons):
        if btn.is_displayed():
            print(f"   Button {idx + 1}:")
            print(f"   - class: {btn.get_attribute('class')}")
            print(f"   - text: {btn.text}")
            print(f"   - HTML: {btn.get_attribute('outerHTML')}")
            print()
    
    print("✓ Done! Check betslip_html.txt for full HTML")
    
    # Don't quit - leave browser open
    print("\nBrowser left open for inspection.")

if __name__ == "__main__":
    main()
