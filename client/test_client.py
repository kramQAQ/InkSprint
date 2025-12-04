# client/test_client.py
import socket

# 目标服务器的 IP 和 端口 (必须和 Server 一致)
HOST = '127.0.0.1'
PORT = 9999

def start_client():
    # 1. 创建 Socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 2. 尝试连接
        print(f"🚀 正在尝试连接服务器 {HOST}:{PORT} ...")
        client_socket.connect((HOST, PORT))
        print("✅ 连接成功！")

        # 3. 发送消息
        message = "你好，我是客户端！这是我的第一条消息。"
        client_socket.sendall(message.encode('utf-8'))
        print("📤 消息已发送")

        # 4. 接收回复
        data = client_socket.recv(1024)
        print(f"📩 收到服务器回复: {data.decode('utf-8')}")

    except ConnectionRefusedError:
        print("❌ 连接失败！请检查服务端是否已经启动。")
    finally:
        # 5. 关闭连接
        client_socket.close()
        print("🔌 连接已关闭")

if __name__ == '__main__':
    start_client()