from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, date

# 定义基类
Base = declarative_base()


class User(Base):
    """用户表：存储账号核心信息"""
    __tablename__ = 'users'

    # 全局自增 ID，作为用户唯一标识
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 登录用
    username = Column(String(50), unique=True, nullable=False, comment="登录昵称")
    password_hash = Column(String(128), nullable=False, comment="加密密码")

    # 找回密码与展示用
    email = Column(String(100), unique=True, nullable=True, comment="绑定邮箱")

    # 个性化展示
    avatar_url = Column(String(255), nullable=True, default="default.jpg", comment="头像路径")
    signature = Column(String(200), nullable=True, comment="个性签名")

    # 系统字段
    created_at = Column(DateTime, default=datetime.now)

    # 关联关系
    detail_records = relationship("DetailRecord", back_populates="user", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class DetailRecord(Base):
    """
    高频明细表：记录每一次具体的写作行为
    数据保留策略：建议仅保留最近 24 小时或最近 7 天的数据，用于展示实时动态。
    """
    __tablename__ = 'detail_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # 核心统计数据
    word_increment = Column(Integer, nullable=False, comment="本次新增字数")

    # 来源追踪 (新增需求)
    source_path = Column(Text, nullable=False, comment="文档路径或URL")
    source_type = Column(String(20), default='local', comment="local 或 web")

    # 时间戳
    timestamp = Column(DateTime, default=datetime.now, index=True)

    # 关联
    user = relationship("User", back_populates="detail_records")

    def __repr__(self):
        return f"<Detail(src={self.source_type}, inc={self.word_increment})>"


class DailyReport(Base):
    """
    每日汇总表：用于生成长期报表
    每天每个用户只有一条记录，永久保存。
    """
    __tablename__ = 'daily_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # 统计日期
    report_date = Column(Date, default=date.today, index=True, comment="统计日期")

    # 当日汇总数据
    total_words = Column(Integer, default=0, comment="当日总字数")
    total_duration = Column(Integer, default=0, comment="当日总专注时长(秒)")

    # 关联
    user = relationship("User", back_populates="daily_reports")

    def __repr__(self):
        return f"<DailyReport(date={self.report_date}, words={self.total_words})>"


class DatabaseManager:
    def __init__(self, db_url='sqlite:///server_data.db'):
        """
        初始化数据库管理器
        :param db_url: 数据库连接字符串
                       本地测试可用 SQLite: 'sqlite:///server_data.db'
                       生产环境推荐 MySQL: 'mysql+pymysql://root:password@localhost/inksprint'
        """
        # echo=False 关闭 SQL 日志打印，保持控制台清爽
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """创建所有表结构"""
        Base.metadata.create_all(self.engine)
        print("[Database] 表结构已更新：User, DetailRecord, DailyReport")

    def get_session(self):
        """获取一个新的会话 (记得使用 with session_scope() 或手动 close)"""
        return self.Session()


# 单例模式
# 如果需要使用 MySQL，请修改下方的连接字符串，例如：
# db_manager = DatabaseManager('mysql+pymysql://root:123456@127.0.0.1:3306/inksprint?charset=utf8mb4')
db_manager = DatabaseManager('sqlite:///server_data.db')

if __name__ == '__main__':
    # 运行此文件进行测试初始化
    # 注意：如果表结构发生重大变化且使用 SQLite，可能需要删除旧的 .db 文件重新生成
    db_manager.init_db()