import time
import socket
import os
import threading
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import hashlib
import base64
from colorama import init, Fore
import platform
from datetime import datetime

init(autoreset=True)
load_dotenv()

SRV_IP = os.getenv("SRV_IP")
SRV_PORT = int(os.getenv("SRV_PORT", "65432"))
SRV_KEY = os.getenv("SRV_KEY")
CLIENT_KEY = os.getenv("CLIENT_KEY")

def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")

def get_cipher(key):
    hashed = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(hashed[:32]))

cipher = get_cipher(CLIENT_KEY)
nickname = input("Enter your nickname: ")

chat_log = []
connected_users = []

def timestamp():
    return datetime.now().strftime("[%H:%M]")

def display_chat():
    clear_screen()
    print("=== Connected Clients ===")
    for u in connected_users:
        if u == nickname:
            print(Fore.GREEN + f"- {u} (You)")
        else:
            print(f"- {u}")
    print("\n=== Simple Encrypted Chat ===\n")
    for msg in chat_log[-20:]:
        print(msg)
    print("\nEnter message:")

def receive(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break

            if data.startswith(b"__USERS__"):
                try:
                    user_list = data.decode().split(":", 1)[1]
                    connected_users.clear()
                    connected_users.extend(user_list.split(",") if user_list else [])
                    display_chat()
                except Exception as e:
                    chat_log.append(Fore.YELLOW + f"{timestamp()} [SYSTEM]: Failed to process user list")
                    display_chat()
                continue

            try:
                decrypted = cipher.decrypt(data).decode()
                sender, content = decrypted.split(":", 1)

                if sender == nickname:
                    chat_log.append(Fore.GREEN + f"{timestamp()} [{sender}]: {content}")
                else:
                    chat_log.append(f"{timestamp()} [{sender}]: {content}")

            except Exception:
                try:
                    sender = data.decode(errors="ignore").split(":", 1)[0]
                except:
                    sender = "Unknown"
                chat_log.append(Fore.YELLOW + f"{timestamp()} [{sender}]: Failed to decode user message")

            display_chat()

        except Exception as e:
            chat_log.append(Fore.RED + f"{timestamp()} [ERROR]: {e}")
            display_chat()
            break

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((SRV_IP, SRV_PORT))
    s.sendall(SRV_KEY.encode())
    s.sendall(nickname.encode())
    time.sleep(1)
    chat_log.append(Fore.CYAN + f"{timestamp()} Connected as {nickname}")
    display_chat()

    threading.Thread(target=receive, args=(s,), daemon=True).start()

    while True:
        try:
            msg = input()
            if msg.lower() == 'exit':
                break
            encrypted = cipher.encrypt(f"{nickname}:{msg}".encode())
            s.sendall(encrypted)
        except KeyboardInterrupt:
            break
