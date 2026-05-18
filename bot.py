import os
import sys
import time
import random
import threading
import requests
import string
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

PROXY_FILE = os.path.join(get_base_path(), "proxy.txt")
ACCOUNTS_FILE = os.path.join(get_base_path(), "accounts.txt")

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class InstagramBot:
    def __init__(self):
        self.proxies = []
        self.cl = Client()
        self.accounts = []
        self.load_proxies()
        self.load_accounts()

    def load_proxies(self):
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line:
                        if line.startswith("socks4 "):
                            clean_proxy = line.replace("socks4 ", "socks4://")
                        elif not line.startswith("socks") and not line.startswith("http"):
                            clean_proxy = f"socks4://{line}"
                        else:
                            clean_proxy = line
                        self.proxies.append(clean_proxy)
            print(f"[+] {len(self.proxies)} proxy yüklendi.")
        else:
            print("[-] proxy.txt bulunamadı!")

    def load_accounts(self):
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r") as f:
                for line in f:
                    if ":" in line:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            u, p = parts
                            self.accounts.append({"username": u, "password": p})
            print(f"[+] {len(self.accounts)} kayıtlı hesap yüklendi.")

    def save_account(self, username, password):
        with open(ACCOUNTS_FILE, "a") as f:
            f.write(f"{username}:{password}\n")
        self.accounts.append({"username": username, "password": password})
        print(f"[+] Hesap {ACCOUNTS_FILE} dosyasına kaydedildi.")

    def check_proxies(self):
        print("[*] Proxyler kontrol ediliyor (Arkaplanda)...")
        valid_proxies = []
        lock = threading.Lock()
        
        def check(proxy):
            try:
                proxies_dict = {"http": proxy, "https": proxy}
                r = requests.get("https://www.instagram.com", proxies=proxies_dict, timeout=5)
                if r.status_code == 200:
                    with lock:
                        valid_proxies.append(proxy)
            except:
                pass

        threads = []
        for p in self.proxies[:15]: # Hızlı başlangıç için az sayıda kontrol
            t = threading.Thread(target=check, args=(p,))
            t.start()
            threads.append(t)
        for t in threads: t.join()
            
        if valid_proxies:
            self.proxies = valid_proxies
        print(f"[+] {len(valid_proxies)} aktif proxy bulundu.")

    def get_random_proxy(self):
        return random.choice(self.proxies) if self.proxies else None

    def create_account(self):
        print("\n[*] Arkaplanda (Headless) hesap oluşturma başlatıldı...")
        proxy = self.get_random_proxy()
        
        # Otomatik veriler
        email = f"{generate_random_string(8)}@gmail.com"
        full_name = f"Bot {generate_random_string(5)}"
        username = generate_random_string(12)
        password = generate_random_string(14) + "!"

        with sync_playwright() as p:
            browser_args = ["--disable-blink-features=AutomationControlled"]
            proxy_settings = None
            if proxy:
                print(f"[*] İşlem şu proxy üzerinden yapılıyor: {proxy}")
                # Playwright expects a dict for proxy if passed to launch
                # or a string for --proxy-server in args. 
                # Let's use the launch parameter for better stability.
                p_parts = proxy.split("://")
                proxy_settings = {"server": proxy}

            try:
                # HEADLESS = TRUE (Tarayıcı açılmaz)
                browser = p.chromium.launch(headless=True, args=browser_args, proxy=proxy_settings)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page = context.new_page()
                stealth(page)
                
                print("[*] Instagram'a bağlanılıyor...")
                page.goto("https://www.instagram.com/accounts/emailsignup/", timeout=90000)
                time.sleep(5)

                # Form doldurma denemesi (Instagram sürekli değiştiği için selectorlar hassastır)
                try:
                    page.fill('input[name="emailOrPhone"]', email)
                    page.fill('input[name="fullName"]', full_name)
                    page.fill('input[name="username"]', username)
                    page.fill('input[name="password"]', password)
                    print(f"[*] Form verileri girildi: {username}")
                    
                    # Kaydol butonuna tıkla
                    page.click('button[type="submit"]')
                    time.sleep(10)
                    
                    # Buradan sonrası genellikle Captcha veya Email onayıdır.
                    # Headless modda bunları geçmek zordur, ancak kullanıcıya durumu bildiririz.
                    print("[!] Hesap oluşturma isteği gönderildi. Eğer Instagram onay istemezse hesap kaydedilecek.")
                    print("[!] Not: Instagram genellikle e-posta onayı veya Captcha ister. Bu durumda işlem başarısız olabilir.")
                    
                    # Başarı kontrolü (basitçe URL değişimi veya ana sayfa elementleri)
                    if "accounts/emailsignup" not in page.url:
                        self.save_account(username, password)
                    else:
                        print("[-] Kayıt tamamlanamadı (Büyük ihtimalle Captcha veya Onay gerekiyor).")
                        # Debug için verileri yine de gösterelim
                        print(f"[?] Denenen bilgiler: {username}:{password}")
                        # Kaydetmek isterse:
                        save_anyway = input("Bu bilgileri yine de accounts.txt'ye kaydedeyim mi? (e/h): ")
                        if save_anyway.lower() == 'e':
                            self.save_account(username, password)

                except Exception as fe:
                    print(f"[-] Form doldurma hatası (Instagram engellemiş olabilir): {fe}")
                    
            except Exception as e:
                print(f"[-] Hata: {e}")
            finally:
                print("[*] İşlem bitti.")

    def login_with_account(self, acc):
        proxy = self.get_random_proxy()
        if proxy: self.cl.set_proxy(proxy)
        try:
            print(f"[*] {acc['username']} giriş yapıyor...")
            self.cl.login(acc['username'], acc['password'])
            return True
        except Exception as e:
            print(f"[-] {acc['username']} hata: {e}")
            return False

    def mass_follow(self):
        if not self.accounts:
            print("[-] Kayıtlı hesap yok.")
            return
        target = input("Takip edilecek kullanıcı: ")
        for acc in self.accounts:
            if self.login_with_account(acc):
                try:
                    user_id = self.cl.user_id_from_username(target)
                    self.cl.user_follow(user_id)
                    print(f"[+] {acc['username']} takip etti.")
                    time.sleep(random.uniform(5, 10))
                except Exception as e: print(f"[-] Hata: {e}")
                self.cl.logout()

    def mass_like(self):
        if not self.accounts:
            print("[-] Kayıtlı hesap yok.")
            return
        url = input("Beğenilecek link: ")
        for acc in self.accounts:
            if self.login_with_account(acc):
                try:
                    media_id = self.cl.media_id(self.cl.media_pk_from_url(url))
                    self.cl.media_like(media_id)
                    print(f"[+] {acc['username']} beğendi.")
                    time.sleep(random.uniform(5, 10))
                except Exception as e: print(f"[-] Hata: {e}")
                self.cl.logout()

def main():
    bot = InstagramBot()
    if bot.proxies: bot.check_proxies()

    while True:
        print("\n" + "="*35)
        print(f"   INSTAGRAM BOT v1.2 (HEADLESS)")
        print(f"   Proxyler: {len(bot.proxies)} | Kayıtlı: {len(bot.accounts)}")
        print("="*35)
        print("1. Hesap Oluştur (Gizli/Proxy)")
        print("2. Tüm Hesaplarla Takip Et")
        print("3. Tüm Hesaplarla Beğen")
        print("4. Çıkış")
        
        choice = input("Seçim: ")
        if choice == '1': bot.create_account()
        elif choice == '2': bot.mass_follow()
        elif choice == '3': bot.mass_like()
        elif choice == '4': break
        else: print("Geçersiz.")

if __name__ == "__main__":
    main()
