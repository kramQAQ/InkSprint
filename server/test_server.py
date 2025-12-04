# server/test_server.py
import socket

# 1. 设置服务器 IP 和 端口
HOST = '127.0.0.1'  # 本地回环地址，只有自己电脑能访问
PORT = 9999  # 端口号，选一个没被占用的（大于1024）


def start_server():
    # 2. 创建 Socket 对象 (IPv4, TCP协议)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 3. 绑定 IP 和 端口
    try:
        server_socket.bind((HOST, PORT))
        print(f"✅ 服务端已启动，正在监听 {HOST}:{PORT} ...")
    except Exception as e:
        print(f"❌ 启动失败，端口可能被占用: {e}")
        return

    # 4. 开始监听 (最大挂起连接数 5)
    server_socket.listen(5)

    while True:
        print("⏳ 等待客户端连接...")
        # 5. 阻塞等待，直到有客户端连接
        conn, addr = server_socket.accept()
        print(f"🔗 既然有一个客户端连接上了！地址: {addr}")

        with conn:
            # 6. 接收数据 (一次最多 1024 字节)
            data = conn.recv(1024)
            if not data:
                break

            msg = data.decode('utf-8')
            print(f"📩 收到消息: {msg}")

            # 7. 发送回复
            reply = f"服务端已收到你的消息: '{msg}'".encode('utf-8')
            conn.sendall(reply)
            print("📤 已回复客户端")

        # 这里的 conn 自动关闭，继续等待下一个循环


if __name__ == '__main__':
    start_server()