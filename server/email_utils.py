import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 配置 (建议放入环境变量或配置文件，不要直接硬编码上传到 GitHub)
SMTP_HOST = "smtp.qq.com"  # 例如 QQ邮箱
SMTP_PORT = 465  # SSL 端口
SENDER_EMAIL = "jiefei182@qq.com"
SENDER_PASS = "xyadinzmxwxwchca"  # 注意：不是登录密码


class EmailManager:
    @staticmethod
    def send_verification_code(to_email, code):
        """发送验证码邮件"""
        subject = "InkSprint 注册验证码"
        content = f"欢迎注册 InkSprint！您的验证码是：{code}\n该验证码 10 分钟内有效。"

        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = Header("InkSprint Admin", 'utf-8')
        message['To'] = Header(to_email, 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')

        try:
            # 使用 SSL 连接
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
            smtp.login(SENDER_EMAIL, SENDER_PASS)
            smtp.sendmail(SENDER_EMAIL, [to_email], message.as_string())
            smtp.quit()
            return True
        except Exception as e:
            print(f"[Email Error] {e}")
            return False