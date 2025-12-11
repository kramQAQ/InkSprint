from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, date

# 定义基类
Base = declarative_base()


class User(Base):
    """用户表：存储账号核心信息"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录账号/ID")
    password_hash = Column(String(128), nullable=False, comment="加密密码")
    nickname = Column(String(50), nullable=True, comment="显示昵称")
    email = Column(String(100), unique=True, nullable=True, comment="绑定邮箱")
    avatar_url = Column(String(255), nullable=True, default="default.jpg", comment="头像路径")
    signature = Column(String(200), nullable=True, comment="个性签名")
    created_at = Column(DateTime, default=datetime.now)

    # 关联关系
    detail_records = relationship("DetailRecord", back_populates="user", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", back_populates="user", cascade="all, delete-orphan")
    saved_sources = relationship("UserSource", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class DetailRecord(Base):
    """高频明细表：记录每一次具体的写作行为(心跳/Session粒度)"""
    __tablename__ = 'detail_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    word_increment = Column(Integer, nullable=False, comment="本次Session新增字数")
    duration_seconds = Column(Integer, default=0, comment="本次Session持续时长")

    # 【新增】补充缺失的字段，用于记录来源
    source_type = Column(String(20), default="unknown", comment="来源类型(local/web)")
    source_path = Column(Text, nullable=True, comment="文件路径或URL")

    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="detail_records")


class DailyReport(Base):
    """每日汇总表：用于生成长期报表"""
    __tablename__ = 'daily_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    report_date = Column(Date, default=date.today, index=True, comment="统计日期")
    total_words = Column(Integer, default=0, comment="当日总字数")

    user = relationship("User", back_populates="daily_reports")


class UserSource(Base):
    """用户绑定的文件源配置"""
    __tablename__ = 'user_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    path = Column(Text, nullable=False)
    source_type = Column(String(20), default='local')  # local or web

    user = relationship("User", back_populates="saved_sources")


class DatabaseManager:
    def __init__(self, db_url='sqlite:///server_data.db'):
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """创建所有表结构"""
        Base.metadata.create_all(self.engine)
        print("[Database] 表结构已更新")

    def get_session(self):
        return self.Session()


db_manager = DatabaseManager('sqlite:///server_data.db')

if __name__ == '__main__':
    db_manager.init_db()