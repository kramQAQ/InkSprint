import socket
import struct
import json
import sys
import os
import time
from PyQt6.QtCore import QThread, pyqtSignal  # ✅ 改用 QThread

# 路径修正
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.security import SecurityManager


class NetworkManager(QThread):  # ✅ 继承 QThread 以支持信号
    """
    客户端网络核心：负责 E2EE 握手与加密通信
    """
    # 定义一个信号：当收到 JSON 消息时触发，传出字典数据
    message_received = pyqtSignal(dict)

    def __init__(self, host='154.83.93.189', port=23456):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.aes_key = None
        self.running = False
        self.connected = False

    def connect_and_handshake(self):
        """建立 TCP 连接并执行安全握手"""
        try:
            print(f"[Net] Connecting to {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)

            # --- 握手步骤 1: 接收服务器 RSA 公钥 ---
            len_bytes = self._recv_exact(4)
            if not len_bytes: return False
            pub_len = struct.unpack('>I', len_bytes)[0]

            server_pub_bytes = self._recv_exact(pub_len)
            server_pub_key = SecurityManager.bytes_to_public_key(server_pub_bytes)

            # --- 握手步骤 2: 生成并发送 AES 密钥 ---
            self.aes_key = SecurityManager.generate_aes_key()
            encrypted_aes_key = SecurityManager.encrypt_with_rsa(server_pub_key, self.aes_key)

            header = struct.pack('>I', len(encrypted_aes_key))
            self.socket.sendall(header + encrypted_aes_key)
            print("[Net] AES Key sent. Secure Channel Established. 🔒")

            self.connected = True
            self.running = True
            return True

        except Exception as e:
            print(f"[Net] Connection Failed: {e}")
            self.connected = False
            return False

    def send_request(self, data_dict):
        """发送加密后的 JSON 请求"""
        if not self.connected or not self.aes_key:
            return

        try:
            json_str = json.dumps(data_dict)
            encrypted_data = SecurityManager.encrypt_aes(self.aes_key, json_str)
            header = struct.pack('>I', len(encrypted_data))
            self.socket.sendall(header + encrypted_data)
        except Exception as e:
            print(f"[Net] Send Error: {e}")
            self.close()

    def _recv_exact(self, num_bytes):
        data = b''
        while len(data) < num_bytes:
            try:
                chunk = self.socket.recv(num_bytes - len(data))
                if not chunk: return None
                data += chunk
            except:
                return None
        return data

    def run(self):
        """接收线程的主循环"""
        while self.running and self.connected:
            try:
                # 1. 读包头
                header = self._recv_exact(4)
                if not header: break
                body_len = struct.unpack('>I', header)[0]

                # 2. 读包体
                body_bytes = self._recv_exact(body_len)
                if not body_bytes: break

                # 3. 解密
                plain_json = SecurityManager.decrypt_aes(self.aes_key, body_bytes)
                response = json.loads(plain_json)

                # 4. ✅ 触发信号，通知 UI 线程
                print(f"[Client Recv] {response}")
                self.message_received.emit(response)

            except Exception as e:
                print(f"[Net] Receive Loop Error: {e}")
                break

        self.close()

    def close(self):
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("[Net] Disconnected.")