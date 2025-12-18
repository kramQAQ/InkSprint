import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr  # 【关键修复】必须导入此函数以解决 NameError

# 配置 (建议放入环境变量或配置文件，不要直接硬编码上传到 GitHub)
SMTP_HOST = "smtp.qq.com"  # 例如 QQ邮箱
SMTP_PORT = 465  # SSL 端口
SENDER_EMAIL = "xuwandong19@foxmail.com"
SENDER_PASS = "iqqxofdcvaicdhbi"  # 注意：不是登录密码



class EmailManager:
    @staticmethod
    def send_verification_code(to_email, code):
        """
        发送验证码邮件 (真实发送模式)
        返回: True (成功) / False (失败)
        """
        print(f"[-] [Email] 正在尝试连接服务器并发送邮件给: {to_email}")

        subject = "InkSprint 注册验证码"
        content = f"欢迎注册 InkSprint！您的验证码是：{code}\n该验证码 10 分钟内有效。"

        message = MIMEText(content, 'plain', 'utf-8')

        # 【核心修复】使用 formataddr 构建标准的 "昵称 <邮箱>" 格式
        # QQ邮箱严格校验 From 头，如果不包含实际邮箱地址会报 550 Error
        message['From'] = formataddr(("InkSprint Admin", SENDER_EMAIL))
        message['To'] = to_email
        message['Subject'] = Header(subject, 'utf-8')

        try:
            # 1. 连接 SMTP 服务器 (使用 SSL 端口 465)
            # timeout 设置为 10 秒，避免网络卡死
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)

            # 如果需要查看极其详细的握手日志，取消下面这行的注释
            # smtp.set_debuglevel(1)

            # 2. 登录
            smtp.login(SENDER_EMAIL, SENDER_PASS)

            # 3. 发送
            smtp.sendmail(SENDER_EMAIL, [to_email], message.as_string())

            # 4. 退出
            smtp.quit()

            print(f"[+] [Email] 邮件已成功发送至 {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"[!] [Email Error] 认证失败 (535): 授权码错误或失效。请重新生成授权码。\n详细信息: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            print(
                f"[!] [Email Error] 连接失败: 无法连接到 SMTP 服务器。可能是网络拦截了端口 {SMTP_PORT}。\n详细信息: {e}")
            return False
        except smtplib.SMTPException as e:
            print(f"[!] [Email Error] SMTP 协议错误: {e}")
            return False
        except Exception as e:
            print(f"[!] [Email Error] 发送发生未知错误: {e}")
            return False


# --- 独立测试模块 ---
# 在 PyCharm 中右键点击此文件 -> Run 'email_utils'
# 或者在终端运行: python server/email_utils.py
if __name__ == '__main__':
    print("=== 开始邮件发送测试 ===")
    # 您可以修改这里为其他邮箱进行测试
    test_target = "xuwandong19@foxmail.com"
    test_code = "888888"

    success = EmailManager.send_verification_code(test_target, test_code)

    if success:
        print("✅ 测试成功! 请检查收件箱。")
    else:
        print("❌ 测试失败，请查看上方的错误日志进行排查。")