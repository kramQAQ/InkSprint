from database import db_manager, User, DetailRecord, DailyReport
from datetime import date
import os


def test_database_logic():
    print("🚀 开始数据库测试...")

    # 1. 初始化建表
    db_manager.init_db()
    session = db_manager.get_session()

    try:
        # --- 2. 模拟用户注册 ---
        print("\n[1/4] 测试用户注册...")
        username = "writer_001"
        user = session.query(User).filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                password_hash="sha256_mock_hash_value",
                email="writer@example.com",
                signature="不写完不睡觉"
            )
            session.add(user)
            session.commit()
            print(f"✅ 用户创建成功: ID={user.id}, Name={user.username}")
        else:
            print(f"ℹ️ 用户已存在: ID={user.id}")

        # --- 3. 模拟客户端上传心跳数据 (DetailRecord) ---
        print("\n[2/4] 测试写入详细记录...")
        # 场景：用户在本地 Word 写了 50 字
        rec1 = DetailRecord(
            user_id=user.id,
            word_increment=50,
            source_path="C:/MyNovel/Chapter1.docx",
            source_type="local"
        )
        # 场景：用户在腾讯文档写了 100 字
        rec2 = DetailRecord(
            user_id=user.id,
            word_increment=100,
            source_path="https://docs.qq.com/doc/DRFN...",
            source_type="web"
        )
        session.add_all([rec1, rec2])
        session.commit()
        print("✅ 两条详细记录已保存")

        # --- 4. 模拟生成/更新日报表 (DailyReport) ---
        print("\n[3/4] 测试更新日报表...")
        today = date.today()
        # 查找今天的日报，没有就新建
        daily = session.query(DailyReport).filter_by(user_id=user.id, report_date=today).first()
        if not daily:
            daily = DailyReport(user_id=user.id, report_date=today, total_words=0)
            session.add(daily)

        # 累加刚才的字数 (50 + 100)
        daily.total_words += 150
        session.commit()
        print(f"✅ 日报更新完毕: 日期={daily.report_date}, 总字数={daily.total_words}")

        # --- 5. 验证数据关联查询 ---
        print("\n[4/4] 验证数据关联性...")
        # 通过用户对象反查所有记录
        print(f"用户 [{user.username}] 的详细流水:")
        for r in user.detail_records:
            print(
                f"  - [{r.timestamp.strftime('%H:%M:%S')}] {r.source_type.upper()}: +{r.word_increment} 字 ({r.source_path})")

        print(f"用户 [{user.username}] 的日报记录:")
        for r in user.daily_reports:
            print(f"  - {r.report_date}: 累计 {r.total_words} 字")

    except Exception as e:
        session.rollback()
        print(f"❌ 测试失败: {e}")
    finally:
        session.close()
        print("\n✨ 测试结束")


if __name__ == '__main__':
    test_database_logic()