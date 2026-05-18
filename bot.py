import os
import sys
import time
import random
import threading
import requests
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

PROXY_FILE = os.path.join(get_base_path(), "proxy.txt")

class InstagramBot:
    def __init__(self):
        self.proxies = []
        self.active_proxy = None
        self.cl = Client()
        self.load_proxies()

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

    def check_proxies(self):
        print("[*] Proxyler kontrol ediliyor (İlk 50)...")
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
        for p in self.proxies[:50]:
            t = threading.Thread(target=check, args=(p,))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
            
        if valid_proxies:
            self.proxies = valid_proxies
        print(f"[+] {len(valid_proxies)} aktif proxy bulundu.")

    def get_random_proxy(self):
        if self.proxies:
            return random.choice(self.proxies)
        return None

    def create_account(self):
        print("\n[*] Hesap oluşturma ekranı açılıyor...")
        proxy = self.get_random_proxy()
        
        with sync_playwright() as p:
            browser_args = ["--disable-blink-features=AutomationControlled"]
            if proxy:
                print(f"[*] Kullanılan Proxy: {proxy}")
                browser_args.append(f"--proxy-server={proxy}")
            
            try:
                browser = p.chromium.launch(headless=False, args=browser_args)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                stealth(page)
                
                page.goto("https://www.instagram.com/accounts/emailsignup/", timeout=60000)
                
                print("[?] Kayıt formunu doldurun ve işlemi tamamlayın.")
                while not page.is_closed():
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[-] Tarayıcı hatası: {e}")
            finally:
                print("[*] Kayıt ekranı kapatıldı.")

    def login(self):
        print("\n--- Giriş Bilgileri ---")
        username = input("Kullanıcı adı: ")
        password = input("Şifre: ")
        
        proxy = self.get_random_proxy()
        if proxy:
            self.cl.set_proxy(proxy)
        
        try:
            print("[*] Giriş yapılıyor...")
            self.cl.login(username, password)
            print("[+] Giriş başarılı!")
            return True
        except Exception as e:
            print(f"[-] Giriş hatası: {e}")
            return False

    def follow_user(self):
        target = input("Takip edilecek kullanıcı adı: ")
        try:
            user_id = self.cl.user_id_from_username(target)
            self.cl.user_follow(user_id)
            print(f"[+] {target} başarıyla takip edildi!")
        except Exception as e:
            print(f"[-] Takip hatası: {e}")

    def like_post(self):
        url = input("Beğenilecek link: ")
        try:
            media_id = self.cl.media_id(self.cl.media_pk_from_url(url))
            self.cl.media_like(media_id)
            print("[+] Beğeni gönderildi!")
        except Exception as e:
            print(f"[-] Beğeni hatası: {e}")

def main():
    bot = InstagramBot()
    if bot.proxies:
        bot.check_proxies()

    while True:
        print("\n" + "="*30)
        print("   INSTAGRAM BOT v1.0")
        print("="*30)
        print("1. Hesap Oluştur")
        print("2. Takip Gönder")
        print("3. Beğeni Gönder")
        print("4. Çıkış")
        
        choice = input("Seçiminiz: ")

        if choice == '1':
            bot.create_account()
        elif choice == '2':
            if bot.login():
                bot.follow_user()
                bot.cl.logout()
        elif choice == '3':
            if bot.login():
                bot.like_post()
                bot.cl.logout()
        elif choice == '4':
            break
        else:
            print("Geçersiz seçim.")

if __name__ == "__main__":
    main()
