import os
import sys
import time
import random
import threading
import requests
import json
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
                        u, p = line.strip().split(":", 1)
                        self.accounts.append({"username": u, "password": p})
            print(f"[+] {len(self.accounts)} kayıtlı hesap yüklendi.")

    def save_account(self, username, password):
        with open(ACCOUNTS_FILE, "a") as f:
            f.write(f"{username}:{password}\n")
        self.accounts.append({"username": username, "password": password})
        print(f"[+] Hesap {ACCOUNTS_FILE} dosyasına kaydedildi.")

    def check_proxies(self):
        print("[*] Proxyler kontrol ediliyor (İlk 20)...")
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
        for p in self.proxies[:20]:
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
        print("\n[*] Hesap oluşturma ekranı açılıyor...")
        print("[!] Kayıt olduktan sonra botun algılaması için lütfen kullanıcı adı ve şifrenizi buraya girin.")
        
        proxy = self.get_random_proxy()
        
        with sync_playwright() as p:
            browser_args = ["--disable-blink-features=AutomationControlled"]
            if proxy: browser_args.append(f"--proxy-server={proxy}")
            
            try:
                browser = p.chromium.launch(headless=False, args=browser_args)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page = context.new_page()
                stealth(page)
                page.goto("https://www.instagram.com/accounts/emailsignup/", timeout=60000)
                
                print("[?] Kayıt işlemini tarayıcıda tamamlayın.")
                while not page.is_closed():
                    time.sleep(1)
                    # Simple check if user logged in
                    if "accounts/emailsignup" not in page.url and "instagram.com/" in page.url:
                         print("[!] Giriş yapılmış görünüyor!")
                         break

                u = input("Oluşturduğunuz Kullanıcı Adı: ")
                p_wd = input("Oluşturduğunuz Şifre: ")
                if u and p_wd:
                    self.save_account(u, p_wd)
                    
            except Exception as e:
                print(f"[-] Hata: {e}")
            finally:
                print("[*] Tarayıcı kapatıldı.")

    def login_with_account(self, acc):
        proxy = self.get_random_proxy()
        if proxy: self.cl.set_proxy(proxy)
        try:
            print(f"[*] {acc['username']} ile giriş yapılıyor...")
            self.cl.login(acc['username'], acc['password'])
            return True
        except Exception as e:
            print(f"[-] {acc['username']} giriş hatası: {e}")
            return False

    def mass_follow(self):
        if not self.accounts:
            print("[-] Önce hesap oluşturmalı veya accounts.txt dosyasına hesap eklemelisiniz.")
            return
        
        target = input("Takip edilecek kullanıcı adı: ")
        for acc in self.accounts:
            if self.login_with_account(acc):
                try:
                    user_id = self.cl.user_id_from_username(target)
                    self.cl.user_follow(user_id)
                    print(f"[+] {acc['username']} -> {target} takip etti.")
                    time.sleep(random.uniform(2, 5))
                except Exception as e:
                    print(f"[-] İşlem hatası: {e}")
                self.cl.logout()

    def mass_like(self):
        if not self.accounts:
            print("[-] Kayıtlı hesap bulunamadı.")
            return
        
        url = input("Beğenilecek gönderi linki: ")
        for acc in self.accounts:
            if self.login_with_account(acc):
                try:
                    media_id = self.cl.media_id(self.cl.media_pk_from_url(url))
                    self.cl.media_like(media_id)
                    print(f"[+] {acc['username']} -> Beğeni gönderdi.")
                    time.sleep(random.uniform(2, 5))
                except Exception as e:
                    print(f"[-] İşlem hatası: {e}")
                self.cl.logout()

def main():
    bot = InstagramBot()
    if bot.proxies: bot.check_proxies()

    while True:
        print("\n" + "="*30)
        print("   INSTAGRAM BOT v1.1")
        print(f"   Proxyler: {len(bot.proxies)} | Hesaplar: {len(bot.accounts)}")
        print("="*30)
        print("1. Hesap Oluştur (Tarayıcı)")
        print("2. Tüm Hesaplarla Takip Et")
        print("3. Tüm Hesaplarla Beğen")
        print("4. Çıkış")
        
        choice = input("Seçiminiz: ")

        if choice == '1':
            bot.create_account()
        elif choice == '2':
            bot.mass_follow()
        elif choice == '3':
            bot.mass_like()
        elif choice == '4':
            break
        else:
            print("Geçersiz seçim.")

if __name__ == "__main__":
    main()
