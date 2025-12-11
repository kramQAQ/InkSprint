import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Date, Boolean
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

    # 好友关系
    friends_sent = relationship("Friend", foreign_keys="[Friend.user_id]", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Friend(Base):
    """好友关系表"""
    __tablename__ = 'friends'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    friend_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), default="accepted")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", foreign_keys=[user_id], back_populates="friends_sent")


class Group(Base):
    """群组/房间表"""
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'))
    is_private = Column(Boolean, default=False)
    description = Column(String(200), nullable=True)

    # 拼字相关状态
    sprint_active = Column(Boolean, default=False)
    sprint_start_time = Column(DateTime, nullable=True)
    sprint_target_words = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    """群成员关联表"""
    __tablename__ = 'group_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    joined_at = Column(DateTime, default=datetime.now)

    group = relationship("Group", back_populates="members")


class GroupMessage(Base):
    """群聊消息表"""
    __tablename__ = 'group_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    user_nickname = Column(String(50))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)

    group = relationship("Group", back_populates="messages")


class DetailRecord(Base):
    """高频明细表"""
    __tablename__ = 'detail_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    word_increment = Column(Integer, nullable=False, comment="本次Session新增字数")
    duration_seconds = Column(Integer, default=0, comment="本次Session持续时长")

    source_type = Column(String(20), default="unknown", comment="来源类型(local/web)")
    source_path = Column(Text, nullable=True, comment="文件路径或URL")

    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="detail_records")


class DailyReport(Base):
    """每日汇总表"""
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
    source_type = Column(String(20), default='local')

    user = relationship("User", back_populates="saved_sources")


class DatabaseManager:
    def __init__(self, db_url=None):
        if db_url is None:
            # 【修复】使用绝对路径，确保无论在哪启动，都使用同一个数据库文件
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, 'server_data.db')
            db_url = f'sqlite:///{db_path}'
            print(f"[Database] Using database file: {db_path}")

        # 添加 check_same_thread=False 以支持多线程
        self.engine = create_engine(db_url, echo=False, connect_args={'check_same_thread': False})
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """创建所有表结构"""
        Base.metadata.create_all(self.engine)
        print("[Database] 表结构已更新")

    def get_session(self):
        return self.Session()


# 初始化时不传参数，让它自动使用绝对路径
db_manager = DatabaseManager()

if __name__ == '__main__':
    db_manager.init_db()