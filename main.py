import os
import re
import requests
from playwright.sync_api import sync_playwright

URL_EVENTO = "https://tourvespucci.it/eventi/visita-a-bordo-venezia/"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_DATE = "02/10"  # Filtra specificamente per il giorno 2 ottobre

def send_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def check_day_two():
    found_slots = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="it-IT"
        )
        page = context.new_page()
        print("Caricamento pagina...")
        page.goto(URL_EVENTO, wait_until="networkidle", timeout=60000)

        selects = page.locator("select")
        if selects.count() > 0:
            date_select = selects.nth(0)
            date_options = date_select.locator("option").all()

            for date_opt in date_options:
                date_text = date_opt.inner_text().strip()
                date_val = date_opt.get_attribute("value") or date_text
                
                # Esegue la ricerca SOLO se la data è quella del 2 Ottobre
                if TARGET_DATE in date_text or TARGET_DATE in date_val:
                    print(f"Seleziono data target: {date_text}")
                    date_select.select_option(value=date_val)
                    page.wait_for_timeout(600)

                    # Controlla tutti gli orari disponibili per il giorno 2
                    if selects.count() > 1:
                        time_select = selects.nth(1)
                        time_options = time_select.locator("option").all()

                        for time_opt in time_options:
                            time_val = time_opt.get_attribute("value") or time_opt.inner_text().strip()
                            if not time_val or "seleziona" in time_val.lower():
                                continue

                            time_select.select_option(value=time_val)
                            page.wait_for_timeout(300)

                            content = page.content()
                            match = re.search(r"Posti\s+Disponibili:\s*(\d+)", content, re.IGNORECASE)
                            sold_out = "Non ci sono posti sufficienti disponibili" in content

                            if match and int(match.group(1)) > 0:
                                found_slots.append(f"📅 Data: {date_text} | ⏰ Ora: {time_val} -> **{match.group(1)} posti**")
                            elif not sold_out:
                                found_slots.append(f"📅 Data: {date_text} | ⏰ Ora: {time_val} -> **Disponibile!**")

        browser.close()
    return found_slots

if __name__ == "__main__":
    print("Avvio verifica posti per il 2 Ottobre...")
    available = check_day_two()
    
    if available:
        details = "\n".join(available)
        msg = f"🚨 *POSTI DISPONIBILI PER IL 2 OTTOBRE!*\n\n{details}\n\n👉 [Prenota Subito]({URL_EVENTO})"
        send_alert(msg)
        print("Alert inviato su Telegram!")
    else:
        print("Nessun posto libero per il 2 ottobre al momento.")
