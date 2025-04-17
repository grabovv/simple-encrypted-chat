import socket
import os
import threading
from dotenv import load_dotenv
from collections import defaultdict
import time

load_dotenv()
SRV_IP = os.getenv("SRV_IP")
SRV_PORT = int(os.getenv("SRV_PORT", "65432"))
SRV_KEY = os.getenv("SRV_KEY")

clients = []
nicknames = {}
request_counts = defaultdict(list)

def rate_limited(ip):
    now = time.time()
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 10]
    return len(request_counts[ip]) > 5

def broadcast(message):
    for client in clients:
        try:
            client.sendall(message)
        except:
            if client in clients:
                clients.remove(client)

def broadcast_user_list():
    user_list = ",".join(nicknames[client] for client in clients if client in nicknames)
    message = f"__USERS__:{user_list}".encode()
    for client in clients:
        try:
            client.sendall(message)
        except:
            if client in clients:
                clients.remove(client)

def handle_client(conn, addr):
    ip = addr[0]
    try:
        key = conn.recv(1024).decode()
        request_counts[ip].append(time.time())
        if rate_limited(ip):
            print(f"[BLOCK] Too many requests from {ip}")
            conn.close()
            return

        if key != SRV_KEY:
            print(f"[REJECT] Wrong key from {ip}")
            conn.close()
            return

        nickname = conn.recv(1024).decode()
        clients.append(conn)
        nicknames[conn] = nickname
        print(f"[JOIN] {nickname} from {ip}")

        broadcast_user_list()

        while True:
            data = conn.recv(4096)
            if not data:
                break
            print(f"[MSG] {nickname} sent data ({len(data)} bytes)")
            broadcast(data)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if conn in clients:
            clients.remove(conn)
        if conn in nicknames:
            print(f"[LEAVE] {nicknames[conn]} disconnected")
            del nicknames[conn]
        broadcast_user_list()
        conn.close()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((SRV_IP, SRV_PORT))
    s.listen()
    print(f"[LISTENING] Server running on {SRV_IP}:{SRV_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()