import socket
import threading
import struct
import json
import sys
import os

# 将项目根目录加入模块搜索路径，确保能 import shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.security import SecurityManager

# 配置
HOST = '127.0.0.1'  # 监听所有网卡
PORT = 23456


class ClientHandler(threading.Thread):
    """
    客户端连接处理线程
    负责：RSA握手 -> 建立AES会话 -> 消息循环 -> 资源回收
    """

    def __init__(self, conn, addr, server_private_key, server_public_key_bytes):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.server_private_key = server_private_key
        self.server_public_key_bytes = server_public_key_bytes
        self.aes_key = None  # 握手成功后存储 AES 密钥
        self.running = True

    def send_packet(self, plain_text_dict):
        """加密并发送数据包"""
        if not self.aes_key:
            return

        # 1. 序列化 JSON
        json_str = json.dumps(plain_text_dict)

        # 2. AES 加密
        encrypted_bytes = SecurityManager.encrypt_aes(self.aes_key, json_str)

        # 3. 封装包头 (4字节长度) + 包体
        header = struct.pack('>I', len(encrypted_bytes))
        self.conn.sendall(header + encrypted_bytes)

    def receive_exact_bytes(self, num_bytes):
        """从 socket 读取指定长度的字节"""
        data = b''
        while len(data) < num_bytes:
            packet = self.conn.recv(num_bytes - len(data))
            if not packet:
                return None
            data += packet
        return data

    def perform_handshake(self):
        """执行 E2EE 握手流程"""
        try:
            print(f"[Handshake] Client {self.addr} connected. Sending Public Key...")

            # 1. 发送服务端 RSA 公钥 (无加密，直接发)
            # 为了简单，握手阶段先发 4字节长度 + 公钥PEM
            pub_len = struct.pack('>I', len(self.server_public_key_bytes))
            self.conn.sendall(pub_len + self.server_public_key_bytes)

            # 2. 接收客户端加密后的 AES 密钥
            # 先读长度
            len_bytes = self.receive_exact_bytes(4)
            if not len_bytes: return False
            msg_len = struct.unpack('>I', len_bytes)[0]

            # 再读内容
            encrypted_aes_key = self.receive_exact_bytes(msg_len)

            # 3. RSA 解密
            self.aes_key = SecurityManager.decrypt_with_rsa(self.server_private_key, encrypted_aes_key)
            print(f"[Handshake] Success. Session Key established for {self.addr}")
            return True

        except Exception as e:
            print(f"[Handshake] Error: {e}")
            return False

    def run(self):
        """线程主入口"""
        if not self.perform_handshake():
            self.conn.close()
            return

        # 进入消息循环
        while self.running:
            try:
                # 1. 读取包头 (4 bytes)
                header = self.receive_exact_bytes(4)
                if not header:
                    break  # 客户端断开

                body_len = struct.unpack('>I', header)[0]

                # 2. 读取包体 (Body)
                body_bytes = self.receive_exact_bytes(body_len)
                if not body_bytes:
                    break

                # 3. AES 解密
                plain_json = SecurityManager.decrypt_aes(self.aes_key, body_bytes)
                request = json.loads(plain_json)

                # 4. 业务逻辑处理 (暂时只做打印和回显)
                print(f"[Recv from {self.addr}] {request}")

                # 模拟回复
                response = {
                    "status": "ok",
                    "msg": f"Server received: {request.get('content', '')}",
                    "type": "response"
                }
                self.send_packet(response)

            except Exception as e:
                print(f"[Error] Connection error with {self.addr}: {e}")
                break

        print(f"[Disconnected] Client {self.addr} left.")
        self.conn.close()


class InkServer:
    def __init__(self):
        # 启动时生成 RSA 密钥对
        print("[Init] Generating RSA Keys...")
        self.private_key, self.public_key = SecurityManager.generate_rsa_keys()
        self.public_key_bytes = SecurityManager.public_key_to_bytes(self.public_key)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []  # 存储所有在线的 handler

    def start(self):
        try:
            self.socket.bind((HOST, PORT))
            self.socket.listen(10)
            print(f"[Server] Running on {HOST}:{PORT}")

            while True:
                conn, addr = self.socket.accept()
                # 为每个连接创建一个新线程
                handler = ClientHandler(conn, addr, self.private_key, self.public_key_bytes)
                handler.start()
                self.clients.append(handler)

        except Exception as e:
            print(f"[Server] Crash: {e}")
        finally:
            self.socket.close()


if __name__ == '__main__':
    server = InkServer()
    server.start()