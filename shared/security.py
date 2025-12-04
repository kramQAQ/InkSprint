# shared/security.py
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecurityManager:
    """
    安全管理器：处理 RSA 握手和 AES-GCM 数据加密
    """

    # ---------------- RSA 部分 (用于交换密钥) ----------------

    @staticmethod
    def generate_rsa_keys():
        """生成 RSA 公钥和私钥对 (仅服务端调用)"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def public_key_to_bytes(public_key):
        """将 RSA 公钥转换为 bytes (以便通过网络发送)"""
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @staticmethod
    def bytes_to_public_key(pem_data):
        """将接收到的 bytes 还原为 RSA 公钥对象"""
        return serialization.load_pem_public_key(pem_data)

    @staticmethod
    def encrypt_with_rsa(public_key, secret_data):
        """用 RSA 公钥加密数据 (客户端用于发送 AES 密钥)"""
        return public_key.encrypt(
            secret_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    @staticmethod
    def decrypt_with_rsa(private_key, encrypted_data):
        """用 RSA 私钥解密数据 (服务端用于获取 AES 密钥)"""
        return private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    # ---------------- AES 部分 (用于实际通信) ----------------

    @staticmethod
    def generate_aes_key():
        """生成一个随机的 AES 密钥 (256位)"""
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def encrypt_aes(key, plaintext_str):
        """
        使用 AES-GCM 加密字符串
        返回: nonce(12字节) + 密文 (二进制拼接在一起)
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 每次加密必须使用唯一的随机数
        data_bytes = plaintext_str.encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
        return nonce + ciphertext  # 将 nonce 附在前面以便解密时使用

    @staticmethod
    def decrypt_aes(key, encrypted_bytes):
        """使用 AES-GCM 解密"""
        aesgcm = AESGCM(key)
        nonce = encrypted_bytes[:12]  # 提取前12字节作为 nonce
        ciphertext = encrypted_bytes[12:]  # 剩下的作为密文
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception:
            return "[解密失败: 数据可能被篡改]"


# ==========================================
#              自我测试模块
# ==========================================
if __name__ == '__main__':
    print("🔐 正在测试安全模块...")

    # 1. 模拟服务端生成 RSA 钥匙
    srv_priv, srv_pub = SecurityManager.generate_rsa_keys()
    print("✅ [Server] RSA 密钥对生成完毕")

    # 2. 模拟网络传输公钥 (Server -> Client)
    pub_bytes = SecurityManager.public_key_to_bytes(srv_pub)
    # --- 假设发送到了客户端 ---
    client_received_pub = SecurityManager.bytes_to_public_key(pub_bytes)
    print("✅ [Client] 收到并还原了服务器公钥")

    # 3. 客户端生成 AES 密钥，并用 RSA 加密发送
    aes_key = SecurityManager.generate_aes_key()
    print(f"🔑 [Client] 生成 AES 会话密钥: {aes_key.hex()[:10]}...")

    encrypted_aes_key = SecurityManager.encrypt_with_rsa(client_received_pub, aes_key)
    # --- 假设发送回了服务端 ---

    # 4. 服务端用私钥解开 AES 密钥
    decrypted_aes_key = SecurityManager.decrypt_with_rsa(srv_priv, encrypted_aes_key)
    print(f"✅ [Server] 解密得到 AES 会话密钥: {decrypted_aes_key.hex()[:10]}...")

    assert aes_key == decrypted_aes_key
    print("🎉 握手成功：双方拥有了相同的 AES 密钥！")

    # 5. 测试实际聊天加密
    msg = "Hello! 这是一个最高机密的拼字计划。"
    cipher = SecurityManager.encrypt_aes(aes_key, msg)
    print(f"\n📝 原文: {msg}")
    print(f"🔒 密文(十六进制): {cipher.hex()[:50]}...")

    plain = SecurityManager.decrypt_aes(decrypted_aes_key, cipher)
    print(f"🔓 解密还原: {plain}")

    if msg == plain:
        print("\n🚀 安全模块测试全部通过！可以集成到系统中了。")