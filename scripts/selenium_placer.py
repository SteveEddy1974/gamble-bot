#!/usr/bin/env python3
"""Selenium-based UI bet placer for Exchange Games (auto-submit OPTIONAL).

Notes:
- This is a best-effort implementation for the Exchange Baccarat page. Web UI
  elements vary and may break; use with caution.
- Default behaviour: launch visible Chrome, attempt login if stored credentials
  are configured, navigate to Exchange Baccarat, attempt to locate the side bet
  and place a BACK bet with given stake and price. Falls back to auto-fill +
  pause if exact elements can't be found.
"""
import argparse
import time
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import load_config

# Selenium imports (installed via requirements)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pyperclip
import csv
import tkinter as tk
from tkinter import messagebox
from datetime import datetime


def confirm_dialog(bet_type: str, price: float, stake: float, timeout: int = 20) -> bool:
    """Show a modal confirmation dialog. Returns True if user confirms, False otherwise.
    If the dialog is closed or timeout expires, treat as decline.
    """
    root = tk.Tk()
    root.withdraw()  # hide main window

    # Create a simple dialog message
    msg = f"Place bet: {bet_type}\nPrice: {price}\nStake: £{stake:.2f}\n\nClick Yes to confirm, No to cancel."
    # Show dialog and wait
    result = messagebox.askyesno("Confirm Bet Placement", msg, parent=root)
    try:
        root.destroy()
    except Exception:
        pass
    return bool(result)


def log_placement(logfile: str, bet_type: str, price: float, stake: float, auto_submit: bool, confirmed: bool, result: str):
    header = ['timestamp','bet_type','price','stake','auto_submit','confirmed','result']
    row = [datetime.utcnow().isoformat() + 'Z', bet_type, price, stake, str(auto_submit), str(confirmed), result]
    write_header = not os.path.exists(logfile)
    try:
        with open(logfile, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(header)
            writer.writerow(row)
    except Exception as e:
        print(f"Failed to write log {logfile}: {e}")


def safe_find(driver, xpath, timeout=2):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except Exception:
        return None


def parse_decimal(text: str):
    if not text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def extract_cell_odds(cell):
    try:
        odds_span = cell.find_element(By.XPATH, ".//span[contains(@class,'cell-odds')]")
        odds_text = odds_span.text.strip()
        return parse_decimal(odds_text)
    except Exception:
        return None


def wait_for_betslip(driver, timeout=10):
    betslip_xpath = (
        "//div[contains(@class,'xgame-betslip') or "
        "contains(@class,'betslip') or "
        "contains(@class,'bet-slip') or "
        "contains(@class,'verify-bets') or "
        "contains(@class,'place-bets')]"
    )
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, betslip_xpath))
        )
    except Exception:
        return None


def wait_for_stake_input(driver, timeout=10):
    stake_xpath = "//div[contains(@class,'xgame-betslip')]//input[@name='stake' and @type='number']"

    def _stake_ready(d):
        try:
            el = d.find_element(By.XPATH, stake_xpath)
            if el.is_displayed() and el.is_enabled():
                return el
        except Exception:
            return False
        return False

    try:
        return WebDriverWait(driver, timeout).until(_stake_ready)
    except Exception:
        return None


def wait_for_submit_button(driver, timeout=10):
    submit_xpath = "//button[contains(@class,'submit-bet')]"

    def _submit_ready(d):
        try:
            btn = d.find_element(By.XPATH, submit_xpath)
            if not btn.is_displayed():
                return False
            class_attr = btn.get_attribute("class") or ""
            disabled_attr = btn.get_attribute("disabled")
            aria_disabled = btn.get_attribute("aria-disabled")
            if disabled_attr or (aria_disabled and aria_disabled.lower() == "true") or "disabled" in class_attr.lower():
                return False
            return btn
        except Exception:
            return False

    try:
        return WebDriverWait(driver, timeout).until(_submit_ready)
    except Exception:
        return None


def wait_for_place_bet_button(driver, timeout=8):
    place_xpath = (
        "//button[contains(@class,'place-bb')] | "
        "//button[contains(text(),'Place Bet')] | "
        "//button[contains(text(),'Place bet')] | "
        "//button[contains(text(),'Place Bet(s)')] | "
        "//button[contains(text(),'Confirm')]"
    )

    def _place_ready(d):
        try:
            candidates = d.find_elements(By.XPATH, place_xpath)
            for btn in candidates:
                if btn.is_displayed() and btn.is_enabled():
                    return btn
        except Exception:
            return False
        return False

    try:
        return WebDriverWait(driver, timeout).until(_place_ready)
    except Exception:
        return None


def login_if_needed(driver, cfg, skip_prompt=False):
    # Check if already logged in by looking for positive indicators
    # Since we can successfully place bets, assume logged in if we can see the game interface
    logged_in_indicators = [
        "//div[contains(@class,'balance')]",
        "//span[contains(@class,'balance')]",
        "//*[contains(text(),'My Bets') or contains(text(),'My bets')]",  # My Bets tab indicates login
        "//div[contains(@class,'account')]",
        "//*[contains(@class,'user-name') or contains(@class,'username')]",
        "//a[contains(text(),'My Account') or contains(text(),'Account')]",
        "//*[contains(@class,'betslip') or contains(@class,'bet-slip')]"  # Bet slip area
    ]
    
    for indicator in logged_in_indicators:
        element = safe_find(driver, indicator, timeout=2)
        if element and element.is_displayed():
            print(f"Already logged in (found indicator)")
            return True
    
    # Not logged in - always prompt user to log in manually
    print("\n" + "="*60)
    print("⚠️  NOT LOGGED IN - PLEASE LOG IN MANUALLY IN THE BROWSER")
    print("="*60)
    if not skip_prompt:
        input("Press Enter once you've logged in to continue...")
    else:
        print("WARNING: Could not verify login, continuing anyway with --skip-confirm")
        return True  # Continue anyway when skip-confirm is used
    
    # Verify login succeeded by checking for indicators again
    for indicator in logged_in_indicators:
        element = safe_find(driver, indicator, timeout=2)
        if element and element.is_displayed():
            print("✓ Login verified!")
            return True
    
    print("Warning: Could not verify login - no balance/account indicators found")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        return False
    
    return True


def place_bet(driver, bet_type, price, stake, side='back', liability_mode='payout', auto_submit=True):
    """Click specified bet in Side bets market, enter stake, and submit.
    
    Args:
        side: 'back' or 'lay'
        liability_mode: 'payout' or 'liability' (only for lay bets)
    Returns (success: bool, msg:str).
    """
    print("Preparing to place bet...")
    
    # Copy stake to clipboard for convenience
    try:
        pyperclip.copy(str(stake))
    except Exception:
        pass

    # First, click on "Side bets market" tab
    print("Clicking 'Side bets market' tab...")
    side_bets_tab = safe_find(driver, "//*[contains(text(),'Side bets market')]", timeout=3)
    if side_bets_tab:
        try:
            driver.execute_script("arguments[0].click();", side_bets_tab)
            print("Clicked Side bets market tab")
            time.sleep(0.5)
        except Exception as e:
            print(f"Could not click tab: {e}")

    # Ensure "Place Bets" tab is active on the right panel
    try:
        place_bets_tab = safe_find(
            driver,
            "//div[contains(@class,'bets-navigation')]//div[contains(@class,'tab-selection')][.//span[contains(text(),'Place Bets')]]",
            timeout=2,
        )
        if place_bets_tab:
            driver.execute_script("arguments[0].click();", place_bets_tab)
            time.sleep(0.3)
    except Exception:
        pass
    
    # Wait for new round to start and side bets to become available
    print("\n" + "="*60)
    print("WAITING FOR NEW ROUND TO START")
    print("Side bets will appear when betting opens...")
    print("="*60)
    
    max_wait = 120  # Wait up to 2 minutes
    waited = 0
    cells = None
    
    while waited < max_wait:
        # Find all bet cells (both Back and Lay)
        # The clickable element is the <td class="cell-table">, which contains <div><span class="cell-odds">
        cells = driver.find_elements(By.XPATH, "//tr[contains(@class,'market-view-row')]//td[contains(@class,'cell-table')][.//span[contains(@class,'cell-odds') and string-length(text()) > 0]]")
        
        # Filter to visible cells only
        cells = [c for c in cells if c.is_displayed()]
        
        # Check if we found any cells
        if cells and len(cells) > 0:
            print(f"\n✓ Side bets are now available! Found {len(cells)} cells")
            break
        
        # Still waiting - show debug info
        if waited == 0:
            print(f"  Checking for available bets...")
        elif waited % 5 == 0:  # Every 5 seconds
            print(f"  Waiting for round to start... ({waited}s elapsed)")
            # Show debug info more frequently
            if waited % 15 == 0:  # Every 15 seconds, show details
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text[:200]
                    print(f"    [Debug] Page text sample: {page_text[:100]}...")
                    all_divs = driver.find_elements(By.XPATH, "//div[contains(@class,'bet')]")
                    print(f"    [Debug] Found {len(all_divs)} divs with 'bet' class")
                except:
                    pass
        
        time.sleep(1)
        waited += 1
    
    if not cells or len(cells) == 0:
        print("\n❌ Timed out waiting for side bets")
        print("Possible reasons:")
        print("  - Not on Side bets market tab")
        print("  - Round already in progress (betting closed)")
        print("  - Page not fully loaded")
        return False, "Timed out waiting for side bets to become available"
    
    # Filter cells by bet type and side (Back/Lay)
    target_cells = []
    
    if bet_type.lower() != "any":
        print(f"Looking for bet type: '{bet_type}' ({side})...")
        
        # Find the row containing the bet type name
        for cell in cells:
            try:
                # Navigate up to the row and check if it contains the bet type text
                row = cell.find_element(By.XPATH, "./ancestor::tr[contains(@class,'market-view-row')]")
                row_text = row.text
                
                # Check if this row matches the bet type
                if bet_type.lower() in row_text.lower():
                    # Now determine if this cell is Back or Lay
                    # Get the cell's position in the row to determine if it's Back or Lay
                    # Only count odds cells to avoid including the name cell
                    odds_cells = row.find_elements(
                        By.XPATH,
                        ".//td[contains(@class,'cell-table')][.//span[contains(@class,'cell-odds')]]",
                    )
                    if cell not in odds_cells or len(odds_cells) < 2:
                        continue
                    cell_index = odds_cells.index(cell)

                    # Typically: first 3 cells are Back, last 3 cells are Lay
                    total_cells = len(odds_cells)
                    is_back_cell = cell_index < total_cells / 2
                    
                    if (side.lower() == 'back' and is_back_cell) or (side.lower() == 'lay' and not is_back_cell):
                        target_cells.append(cell)
            except Exception as e:
                continue
        
        if target_cells:
            print(f"✓ Found {len(target_cells)} matching cells for '{bet_type}' ({side})")
        else:
            print(f"❌ Could not find any {side} cells for '{bet_type}'")
            print(f"   Available bets:")
            # Show available bet types
            rows = driver.find_elements(By.XPATH, "//tr[contains(@class,'market-view-row')]")
            for row in rows[:10]:
                try:
                    if row.text:
                        print(f"   - {row.text.splitlines()[0]}")
                except:
                    pass
            return False, f"Bet type '{bet_type}' not found"
    else:
        # "any" bet type - filter by side only
        print(f"Selecting any available {side} bet...")
        for cell in cells:
            try:
                row = cell.find_element(By.XPATH, "./ancestor::tr[contains(@class,'market-view-row')]")
                odds_cells = row.find_elements(
                    By.XPATH,
                    ".//td[contains(@class,'cell-table')][.//span[contains(@class,'cell-odds')]]",
                )
                if cell not in odds_cells or len(odds_cells) < 2:
                    continue
                cell_index = odds_cells.index(cell)
                total_cells = len(odds_cells)
                is_back_cell = cell_index < total_cells / 2
                
                if (side.lower() == 'back' and is_back_cell) or (side.lower() == 'lay' and not is_back_cell):
                    target_cells.append(cell)
            except:
                continue
        
        print(f"✓ Found {len(target_cells)} {side} cells")
    
    if not target_cells:
        return False, f"No {side} cells available"

    # If a target price is provided, filter or prioritize by odds
    if price is not None:
        odds_matches = []
        odds_candidates = []
        for cell in target_cells:
            odds_val = extract_cell_odds(cell)
            if odds_val is None:
                continue
            odds_candidates.append((cell, odds_val))
            if abs(odds_val - float(price)) <= 0.01:
                odds_matches.append((cell, odds_val))

        if odds_matches:
            target_cells = [c for c, _ in odds_matches]
            print(f"✓ Found {len(target_cells)} cells matching price {price}")
        elif odds_candidates:
            # Pick the closest odds if no exact match
            closest = sorted(odds_candidates, key=lambda x: abs(x[1] - float(price)))[0]
            target_cells = [closest[0]]
            print(f"⚠ No exact odds match for {price}. Using closest: {closest[1]}")
        else:
            print("⚠ Could not read odds from target cells; proceeding without price filter")
    
    # Try clicking multiple cells until one opens the bet slip
    bet_slip_opened = False
    for cell_index in range(min(5, len(target_cells))):  # Try up to 5 different cells
        try:
            cell_to_click = target_cells[cell_index]
            cell_text = cell_to_click.text[:20] if cell_to_click.text else "no text"
            cell_tag = cell_to_click.tag_name
            print(f"Attempt {cell_index + 1}: Target <{cell_tag}> text='{cell_text}'")
            
            # Scroll the element into the center of view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell_to_click)
            time.sleep(0.5)
            
            # Try both regular click and JS click
            try:
                cell_to_click.click()  # Try native click first
                print(f"  → Clicked (native)")
            except:
                driver.execute_script("arguments[0].click();", cell_to_click)
                print(f"  → Clicked (JS)")
            
            # Wait longer for bet slip to appear
            time.sleep(2.5)
            
            # Debug: Check what's visible on page
            try:
                page_sample = driver.find_element(By.TAG_NAME, "body").text[:500]
                if "stake" in page_sample.lower() or "liability" in page_sample.lower():
                    print(f"  [Debug] Page contains 'stake' or 'liability' keywords")
            except:
                pass
            
            # Check if bet slip appeared - try multiple selectors
            bet_slip = wait_for_betslip(driver, timeout=6)
            if bet_slip:
                print("✓ Bet slip appeared!")
                bet_slip_opened = True
                break
            
            # Check for any input fields that might be stake
            inputs = driver.find_elements(By.XPATH, "//input[@type='number' or @type='text']")
            visible_inputs = [inp for inp in inputs if inp.is_displayed()]
            if visible_inputs:
                print(f"  [Debug] Found {len(visible_inputs)} visible inputs")
                for inp in visible_inputs[:3]:
                    inp_name = inp.get_attribute('name') or 'no-name'
                    inp_value = inp.get_attribute('value') or ''
                    print(f"    Input: name='{inp_name}' value='{inp_value}'")
            
            print(f"  ✗ Bet slip did not appear, trying next cell...")
            time.sleep(0.5)
                    
        except Exception as e:
            print(f"  Error with cell {cell_index + 1}: {e}")
            continue
    
    if not bet_slip_opened:
        print("\n❌ ERROR: Could not open bet slip after trying multiple cells")
        print("   Possible reasons:")
        print("   - Betting not available (between rounds)")
        print("   - Market suspended")
        print("   - All prices unavailable")
        return False, "Could not open bet slip"

    # Now look for stake input field
    print("Looking for stake input...")
    
    # For LAY bets, select Payout or Liability radio button first
    if side.lower() == 'lay':
        print(f"LAY bet: Selecting '{liability_mode}' mode...")
        time.sleep(1)
        
        try:
            # Find the radio button for the selected mode
            if liability_mode.lower() == 'payout':
                radio_btn = driver.find_element(By.XPATH, "//input[@type='radio' and @value='Payout'] | //label[contains(text(),'Payout')]//input[@type='radio']")
            else:  # liability
                radio_btn = driver.find_element(By.XPATH, "//input[@type='radio' and @value='Liability'] | //label[contains(text(),'Liability')]//input[@type='radio']")
            
            if not radio_btn.is_selected():
                driver.execute_script("arguments[0].click();", radio_btn)
                print(f"✓ Selected '{liability_mode}' radio button")
                time.sleep(0.5)
            else:
                print(f"✓ '{liability_mode}' already selected")
        except Exception as e:
            print(f"⚠️  Could not find/select {liability_mode} radio button: {e}")
            print("   Continuing anyway...")
    
    # Wait longer for bet slip to fully load and become interactive
    time.sleep(2.5)

    # If a target price is provided, set the odds input
    if price is not None:
        try:
            odd_input = driver.find_element(
                By.XPATH,
                "//div[contains(@class,'xgame-betslip')]//input[@name='odd' and @type='number']",
            )
            if odd_input.is_displayed() and odd_input.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView(true);", odd_input)
                time.sleep(0.2)
                try:
                    driver.execute_script("arguments[0].click();", odd_input)
                except Exception:
                    pass
                driver.execute_script(f"arguments[0].value = '{price}';", odd_input)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", odd_input)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", odd_input)
                print(f"✓ Set odds to {price}")
        except Exception as e:
            print(f"⚠️  Could not set odds input: {e}")
    
    # Try multiple approaches to find the stake field
    stake_field = wait_for_stake_input(driver, timeout=8)
    if stake_field:
        print("✓ Found stake field via explicit wait")

    # Try up to 5 times with increasing delays
    for attempt in range(5):
        if stake_field:
            break
        # Approach 1: Most reliable - exact selector from bet slip structure
        try:
            stake_field = driver.find_element(By.XPATH, "//div[contains(@class,'xgame-betslip')]//input[@name='stake' and @type='number']")
            if stake_field.is_displayed() and stake_field.is_enabled():
                print(f"✓ Found stake field in bet slip (attempt {attempt + 1})")
                break
        except:
            pass
        
        # Approach 2: Direct lookup by name="stake"
        if not stake_field:
            try:
                stake_field = driver.find_element(By.NAME, "stake")
                if stake_field.is_displayed() and stake_field.is_enabled():
                    print(f"✓ Found stake field by name='stake' (attempt {attempt + 1})")
                    break
            except:
                pass
        
        # Approach 3: By class name with name attribute
        if not stake_field:
            try:
                stake_inputs = driver.find_elements(By.CLASS_NAME, "stake-input")
                for inp in stake_inputs:
                    if inp.get_attribute('name') == 'stake' and inp.is_displayed() and inp.is_enabled():
                        stake_field = inp
                        print(f"✓ Found stake field by class='stake-input' with name='stake' (attempt {attempt + 1})")
                        break
            except:
                pass
        
        # Approach 4: Look in bet-content container
        if not stake_field:
            try:
                stake_field = driver.find_element(By.XPATH, "//div[contains(@class,'bet-content')]//input[@name='stake']")
                if stake_field.is_displayed() and stake_field.is_enabled():
                    print(f"✓ Found stake field in bet-content (attempt {attempt + 1})")
                    break
            except:
                pass
        
        # Approach 5: Any visible input with name=stake
        if not stake_field:
            try:
                stake_inputs = driver.find_elements(By.XPATH, "//input[@name='stake']")
                for inp in stake_inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        stake_field = inp
                        print(f"✓ Found visible stake field (attempt {attempt + 1})")
                        break
            except:
                pass
        
        if not stake_field and attempt < 4:
            print(f"  Attempt {attempt + 1}/5: Stake field not found, waiting...")
            time.sleep(1.5)
    
    # Fallback: Look for ANY visible number input (last resort)
    if not stake_field:
        # Wait a bit more in case bet slip is still loading
        time.sleep(2)
        
        inputs = driver.find_elements(By.XPATH, "//input[@type='number'] | //input[@type='text']")
        print(f"Fallback: Found {len(inputs)} input fields total")
        
        visible_stake_inputs = []
        for inp in inputs:
            try:
                if inp.is_displayed() and inp.is_enabled():
                    name = inp.get_attribute('name') or ''
                    class_name = inp.get_attribute('class') or ''
                    placeholder = inp.get_attribute('placeholder') or ''
                    
                    print(f"  Input: name='{name}', class='{class_name}', placeholder='{placeholder}'")
                    
                    # Skip login/password fields
                    if 'user' in name.lower() or 'email' in name.lower() or 'pass' in name.lower():
                        print(f"    → Skipping (login field)")
                        continue
                    if 'login' in class_name.lower() or 'username' in class_name.lower():
                        print(f"    → Skipping (username field)")
                        continue
                    
                    # Prioritize stake-related fields
                    if name == 'stake' or 'stake' in class_name.lower() or 'stake' in placeholder.lower():
                        stake_field = inp
                        print(f"  ✓ Found stake field (fallback match on keyword)")
                        break
                    
                    # Collect other visible inputs as candidates
                    visible_stake_inputs.append(inp)
            except Exception as e:
                continue
        
        # If still no stake field, try first visible numeric input
        if not stake_field and visible_stake_inputs:
            stake_field = visible_stake_inputs[0]
            print(f"  → Using first visible input as stake field")
    
    if stake_field:
        try:
            # Scroll to and focus on the field
            driver.execute_script("arguments[0].scrollIntoView(true);", stake_field)
            time.sleep(0.3)
            
            # Try clicking first to activate
            try:
                driver.execute_script("arguments[0].click();", stake_field)
                time.sleep(0.2)
            except:
                pass
            
            # Try using JavaScript to set the value directly
            try:
                driver.execute_script(f"arguments[0].value = '{stake}';", stake_field)
                # Trigger input events
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", stake_field)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", stake_field)
                
                # Verify the value was set correctly
                actual_value = stake_field.get_attribute('value')
                print(f"✓ Entered stake via JS: {stake} (field shows: {actual_value})")
                
                if actual_value != str(stake):
                    print(f"⚠ WARNING: Stake mismatch! Expected {stake}, field shows {actual_value}")
                    # Try again with send_keys
                    stake_field.clear()
                    time.sleep(0.3)
                    stake_field.send_keys(str(stake))
                    actual_value = stake_field.get_attribute('value')
                    print(f"  Retried with send_keys, field now shows: {actual_value}")
                
                time.sleep(0.5)
            except Exception as js_err:
                # Fall back to regular send_keys
                print(f"JS method failed, trying send_keys: {js_err}")
                stake_field.clear()
                time.sleep(0.2)
                stake_field.send_keys(str(stake))
                print(f"✓ Entered stake: {stake}")
                time.sleep(0.5)
        except Exception as e:
            print(f"Error entering stake: {e}")
            return False, f"Could not enter stake: {e}"
    else:
        print("❌ Stake input field not found")
        # Save screenshot for debugging
        try:
            driver.save_screenshot("bet_slip_error.png")
            print("Saved screenshot to: bet_slip_error.png")
        except:
            pass
        return False, "Stake input not found in bet slip"

    # Auto-submit if requested
    if auto_submit:
        print("Looking for Submit button...")
        
        # Try to find the Submit button with multiple approaches
        submit_btn = wait_for_submit_button(driver, timeout=10)
        if submit_btn:
            btn_class = submit_btn.get_attribute('class') or ''
            print(f"  Found enabled Submit button: class='{btn_class[:50]}'")
        else:
            # Fallback: Look for any submit button (even if disabled)
            try:
                submit_candidates = driver.find_elements(By.XPATH, "//button[contains(@class, 'submit') or contains(text(),'Submit')]")
                for btn in submit_candidates:
                    if btn.is_displayed():
                        btn_text = btn.text or btn.get_attribute('value') or ''
                        btn_class = btn.get_attribute('class') or ''
                        print(f"  Found button: text='{btn_text}', class='{btn_class[:50]}'")
                        if 'submit' in btn_text.lower() or 'submit' in btn_class.lower():
                            submit_btn = btn
                            break
            except:
                pass
        
        if submit_btn:
            try:
                btn_info = f"{submit_btn.tag_name}, text='{submit_btn.text[:20]}', visible={submit_btn.is_displayed()}"
                print(f"Clicking Submit button: {btn_info}")
                
                # Scroll into view first
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                time.sleep(0.3)
                
                # Click
                driver.execute_script("arguments[0].click();", submit_btn)
                time.sleep(2)  # Wait for verification screen
                print("✓ Clicked Submit")
                
                # Now look for "Place Bet(s)" confirmation button (if confirmation step appears)
                print("Looking for Place Bet(s) button...")
                place_bet_btn = wait_for_place_bet_button(driver, timeout=6)

                if place_bet_btn:
                    btn_text = place_bet_btn.text or ''
                    btn_class = place_bet_btn.get_attribute('class') or ''
                    print(f"  Found: text='{btn_text}' class='{btn_class[:50]}'")
                    print("Clicking Place Bet(s) button...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", place_bet_btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", place_bet_btn)
                    time.sleep(3)  # Wait for bet to process
                    print("✓ Bet placed!")
                else:
                    print("⚠ No Place Bet(s) confirmation found. Proceeding to verification...")
                
                # Check if we got logged out
                login_indicators = driver.find_elements(By.XPATH, "//a[contains(text(),'Login') or contains(text(),'Log in') or contains(text(),'Sign in')]")
                if login_indicators and any(elem.is_displayed() for elem in login_indicators):
                    print("\n❌ ERROR: LOGGED OUT after placing bet!")
                    print("   This happens when:")
                    print("   - Session expired")
                    print("   - Betfair detected automation/Selenium")
                    print("   - Security challenge triggered")
                    print("\n   Please log in manually and try again")
                    return False, "Logged out after placing bet - session lost"
                
                # Verify bet appears in "My Bets"
                print("\nVerifying bet placement...")
                time.sleep(1)
                
                # Click "My Bets" tab - try multiple methods
                try:
                    # First try clicking by text
                    my_bets_elements = driver.find_elements(By.XPATH, "//*[text()='My Bets']")
                    if not my_bets_elements:
                        # Try partial text match
                        my_bets_elements = driver.find_elements(By.XPATH, "//*[contains(text(),'My Bet')]")
                    
                    if my_bets_elements:
                        driver.execute_script("arguments[0].scrollIntoView(true);", my_bets_elements[0])
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", my_bets_elements[0])
                        print("✓ Clicked My Bets tab")
                        time.sleep(2)
                        
                        # Look for bet entries or "no bets" message
                        page_text = driver.find_element(By.TAG_NAME, "body").text
                        
                        if "do not have any bets" in page_text or "no bets" in page_text.lower():
                            print("❌ WARNING: 'My Bets' shows NO BETS - bet was likely REJECTED")
                            print("   Common rejection reasons:")
                            print("   - Stake too small (minimum £2 on Exchange)")
                            print("   - Market suspended/closed")
                            print("   - Insufficient balance")
                            return False, "Bet submitted but REJECTED - does not appear in My Bets"
                        elif str(stake) in page_text or f"£{stake}" in page_text or f"0.{int(stake*100)}" in page_text:
                            print(f"✓ VERIFIED: Bet with stake £{stake} found in My Bets")
                            return True, "Bet submitted and verified in My Bets"
                        else:
                            # Look for any monetary values
                            bet_entries = driver.find_elements(By.XPATH, "//*[contains(text(),'£')]")
                            if bet_entries and len(bet_entries) > 5:  # More than just header text
                                print(f"✓ Found bet-related content in My Bets ({len(bet_entries)} monetary values)")
                                return True, "Bet submitted (appears to be accepted)"
                            else:
                                print("⚠ My Bets tab opened but could not confirm bet presence")
                                return True, "Bet submitted (verification inconclusive)"
                    else:
                        print("⚠ Could not find My Bets tab element")
                        return True, "Bet submitted (could not verify)"
                except Exception as verify_err:
                    print(f"⚠ Error during verification: {verify_err}")
                    return True, f"Bet submitted (verification error: {verify_err})"
                
            except Exception as e:
                print(f"Error clicking submit: {e}")
                return False, f"Submit button found but could not click: {e}"
        else:
            print("Submit button not found")
            return False, "Submit button not found; stake entered. Please submit manually."
    else:
        return False, "Auto-submit disabled; stake entered. Please submit manually."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bet-type', required=True)
    parser.add_argument('--price', type=float, required=True)
    parser.add_argument('--stake', type=float, required=True)
    parser.add_argument('--side', choices=['back', 'lay'], default='back', help='Back or Lay')
    parser.add_argument('--liability-mode', choices=['payout', 'liability'], default='payout', help='For Lay bets: payout or liability')
    parser.add_argument('--auto-submit', action='store_true', default=False)
    parser.add_argument('--skip-confirm', action='store_true', default=False, help='Skip confirmation dialog')
    parser.add_argument('--continuous', action='store_true', default=False, help='Place bets continuously every round')
    parser.add_argument('--rounds', type=int, default=None, help='Number of rounds to bet (with --continuous)')
    parser.add_argument('--headless', action='store_true', default=False)
    args = parser.parse_args()
    
    # Validate minimum stake for Betfair Exchange
    if args.stake < 2.0:
        print(f"\n⚠️  WARNING: Stake £{args.stake} is below Betfair Exchange minimum of £2.00")
        print("   The bet will likely be REJECTED by Betfair")
        print("   Recommended: Use --stake 2.0 or higher\n")
        if not args.skip_confirm:
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return

    cfg = load_config()

    # Connect to existing Chrome instance on port 9222
    print("Connecting to existing Chrome instance...")
    try:
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        # Use system ChromeDriver without online version check
        driver = webdriver.Chrome(options=options)
        print("Connected to existing Chrome window!")
    except Exception as e:
        print(f"ERROR: Could not connect to Chrome: {e}")
        print("\nPlease make sure Chrome is running with:")
        print('  chrome.exe --remote-debugging-port=9222')
        print("\nOr run: scripts\\start_chrome.bat")
        return 1
    logfile = cfg.get('bot', {}).get('ui_log_file', 'ui_placements.csv')
    confirmed = False
    try:
        # Check current URL
        current_url = driver.current_url
        print(f"Current page: {current_url}")
        
        # Navigate to Exchange Baccarat if not already there
        if 'exchange-baccarat' not in current_url:
            print("Navigating to Exchange Baccarat...")
            driver.get('https://games.betfair.com/exchange-baccarat/standard/')
            time.sleep(1)
        else:
            print("Already on Exchange Baccarat page")

        # Dismiss cookie banner if present
        cookie_xpaths = [
            "//button[contains(text(),'Accept') or contains(text(),'Accept All') or contains(text(),'I Accept') or contains(text(),'ACCEPT')]",
            "//button[contains(@id,'accept') or contains(@id,'Accept') or contains(@class,'accept')]",
            "//a[contains(text(),'Accept') or contains(text(),'Accept All')]"
        ]
        for xp in cookie_xpaths:
            cookie_btn = safe_find(driver, xp, timeout=2)
            if cookie_btn:
                try:
                    cookie_btn.click()
                    print("Dismissed cookie banner")
                    time.sleep(1)
                    break
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", cookie_btn)
                        print("Dismissed cookie banner (JS)")
                        time.sleep(1)
                        break
                    except Exception:
                        pass

        login_if_needed(driver, cfg, skip_prompt=args.skip_confirm)

        # If auto-submit and confirmation required (unless skip-confirm flag), show confirmation dialog
        if args.auto_submit and not args.skip_confirm and cfg.get('bot', {}).get('ui_require_confirmation', True):
            confirmed = confirm_dialog(args.bet_type, args.price, args.stake)
            if not confirmed:
                print('User declined confirmation. Aborting auto-submit.')
                log_placement(logfile, args.bet_type, args.price, args.stake, args.auto_submit, False, 'declined_by_user')
                return
        else:
            confirmed = True  # Skip confirm flag or auto_submit disabled

        # Continuous mode: place bets repeatedly
        if args.continuous:
            rounds_placed = 0
            max_rounds = args.rounds if args.rounds else float('inf')
            
            print("\n" + "="*60)
            print("CONTINUOUS MODE ENABLED")
            if args.rounds:
                print(f"Will place {args.rounds} bets")
            else:
                print("Will place bets continuously (Ctrl+C to stop)")
            print("="*60 + "\n")
            
            while rounds_placed < max_rounds:
                try:
                    rounds_placed += 1
                    print(f"\n{'='*60}")
                    print(f"ROUND {rounds_placed}" + (f" / {args.rounds}" if args.rounds else ""))
                    print(f"{'='*60}\n")
                    
                    success, msg = place_bet(driver, args.bet_type, args.price, args.stake, 
                                            side=args.side, liability_mode=args.liability_mode, 
                                            auto_submit=args.auto_submit)
                    print('RESULT:', success, msg)
                    log_placement(logfile, args.bet_type, args.price, args.stake, args.auto_submit, bool(confirmed), msg)
                    
                    if not success:
                        print("⚠️  Bet placement failed, waiting 5 seconds before retry...")
                        time.sleep(5)
                        continue
                    
                    # Wait for round to finish (check if betting becomes unavailable)
                    print("\nWaiting for round to finish...")
                    time.sleep(10)  # Wait a bit for round to complete
                    
                    # Click back to "Place Bets" tab to prepare for next round
                    try:
                        place_bets_tab = driver.find_elements(By.XPATH, "//*[text()='Place Bets']")
                        if place_bets_tab:
                            driver.execute_script("arguments[0].click();", place_bets_tab[0])
                            print("✓ Returned to Place Bets tab")
                            time.sleep(1)
                    except:
                        pass
                    
                    print(f"✓ Round {rounds_placed} complete. Waiting for next round...")
                    time.sleep(2)
                    
                except KeyboardInterrupt:
                    print(f"\n\nStopped by user after {rounds_placed} rounds")
                    break
                except Exception as e:
                    print(f"Error in round {rounds_placed}: {e}")
                    log_placement(logfile, args.bet_type, args.price, args.stake, args.auto_submit, bool(confirmed), f'exception_round_{rounds_placed}:{e}')
                    time.sleep(5)
                    continue
            
            print(f"\n{'='*60}")
            print(f"CONTINUOUS MODE FINISHED: {rounds_placed} bets placed")
            print(f"{'='*60}\n")
        else:
            # Single bet mode
            success, msg = place_bet(driver, args.bet_type, args.price, args.stake, 
                                    side=args.side, liability_mode=args.liability_mode,
                                    auto_submit=args.auto_submit)
            print('RESULT:', success, msg)
            log_placement(logfile, args.bet_type, args.price, args.stake, args.auto_submit, bool(confirmed), msg)

            if not success:
                print('Please finish placement manually.')
                input('Press Enter to close browser when done...')
    except Exception as e:
        print('Exception during placing:', e)
        log_placement(logfile, args.bet_type, args.price, args.stake, args.auto_submit, bool(confirmed), f'exception:{e}')
        input('Press Enter to close browser...')


if __name__ == '__main__':
    main()
