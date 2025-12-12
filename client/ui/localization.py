# client/ui/localization.py

STRINGS = {
    # --- 全局/通用 ---
    "app_name": "InkSprint",
    "warn_title": "提示",
    "error_title": "错误",
    "success_title": "成功",
    "confirm_title": "确认",
    "lbl_loading": "加载中...", # 新增

    # --- 托盘菜单 (System Tray) ---
    "tray_show": "显示主面板",
    "tray_float": "悬浮模式",
    "tray_quit": "退出",
    "msg_conn_fail_title": "连接失败",
    "msg_conn_fail_text": "无法连接到服务器 \n请先运行 server/main.py",

    # --- 登录窗口 (Auth) ---
    "window_title_auth": "InkSprint 认证",
    "login_btn": "登录",
    "create_account_link": "创建账号",
    "forgot_password_link": "忘记密码？",
    "register_header": "注册账号",
    "register_btn": "注册",
    "back_login_link": "← 返回登录",
    "reset_header": "重置密码",
    "send_code_btn": "发送验证码",
    "send_code_btn_sent": "已发送..",
    "reset_btn": "重置密码",
    "placeholder_user": "用户名",
    "placeholder_user_req": "用户名 *",
    "placeholder_pwd": "密码",
    "placeholder_pwd_req": "密码 *",
    "placeholder_email": "邮箱 (用于找回密码)",
    "placeholder_code": "验证码",
    "placeholder_new_pwd": "新密码",

    # 登录弹窗/错误
    "warn_enter_all": "请输入用户名和密码",
    "warn_user_pwd_req": "用户名和密码不能为空",
    "warn_enter_user_first": "请先输入用户名",
    "warn_fields_req": "所有字段都必填",
    "title_login_fail": "登录失败",
    "title_reg_success": "注册成功",
    "title_reg_fail": "注册失败",
    "title_sent": "已发送",
    "title_reset_fail": "重置失败",

    # --- 主界面 (Dashboard) ---
    "window_title_dash": "InkSprint 面板",
    "nav_dashboard": "主页",
    "nav_analytics": "统计",
    "nav_social": "社交",
    "nav_settings": "设置",
    "theme_dark": "🌙 深色",
    "theme_light": "☀ 浅色",

    # 统计卡片
    "stat_today": "今日字数",
    "stat_session": "本次: +{}",
    "stat_speed": "当前速度",
    "unit_wph": "字/小时",

    # 底部卡片
    "sources_title": "监控源 ({}/10)",
    "btn_local": "➕ 本地",
    "btn_online": "🌐 在线",
    "timer_title": "专注番茄钟",
    "check_float": "悬浮",

    # 设置页
    "settings_title": "设置",
    "profile_header": "个人设置",
    "lbl_uid": "用户 ID:",
    "lbl_nick": "昵称:",
    "lbl_email": "邮箱:",
    "lbl_avatar": "头像:",
    "placeholder_nick": "显示名称",
    "placeholder_bind_email": "绑定邮箱",
    "btn_change_avatar": "更换头像",
    "appearance_header": "外观",
    "lbl_accent": "主题色:",
    "btn_save": "保存修改",

    # 设置页弹窗
    "msg_nick_empty": "昵称不能为空！",
    "msg_profile_sent": "个人信息更新请求已发送。",
    "dialog_select_avatar": "选择头像",
    "dialog_img_files": "图片文件 (*.png *.jpg *.jpeg)",
    "dialog_select_doc": "选择文档",
    "dialog_doc_files": "文档 (*.docx *.txt)",
    "dialog_add_web_title": "添加网页源",
    "dialog_add_web_label": "链接:",
    "menu_remove": "移除",

    # --- 统计页 (Analytics) ---
    "analytics_title_header": "活动统计",
    "btn_week": "周",
    "btn_month": "月",
    "btn_year": "年",
    "graph_title": "贡献热力图 (近一年)",
    "btn_view_details": "查看近期明细 (3天)",
    "dialog_details_title": "近期活动明细",
    "col_time": "时间",
    "col_added": "新增字数",
    "col_duration": "时长 (秒)",

    # --- 社交页 (Social) ---
    "tab_groups": "房间",
    "tab_friends": "好友",

    # 好友相关
    "search_placeholder": "搜索用户ID或昵称",
    "btn_search_user": "搜索用户", # 修改文案
    "btn_add_friend": "添加好友",
    "btn_friend_reqs": "好友请求",
    "btn_refresh_list": "刷新列表",
    "dialog_friend_req_title": "好友请求",
    "item_no_reqs": "暂无待处理请求。",
    "lbl_dbl_click": "双击列表项进行处理:",
    "msg_new_req": "你收到一个新的好友请求！",
    "msg_req_confirm_title": "回应请求", # 优化文案
    "msg_req_confirm_fmt": "接受来自 {} 的请求?",
    "msg_found_user_title": "找到用户",
    "msg_add_confirm_fmt": "添加 {} ({}) 为好友?",
    "msg_not_found_title": "未找到",
    "msg_user_not_found": "用户不存在。",
    "msg_friend_list_updated": "好友列表已更新！", # 新增

    # 房间相关
    "btn_create_group": "➕ 创建房间",
    "btn_refresh_lobby": "🔄 刷新大厅",
    "lbl_room_name_fmt": "房间: {}",
    "btn_leave_room": "离开房间",
    "btn_float_chat": "悬浮聊天",
    "btn_float_rank": "悬浮排行",
    "chat_placeholder": "输入消息...",
    "btn_send": "发送",
    "lbl_leaderboard": "排行榜",
    "lbl_owner_ctrl": "房主控制",
    "status_sprint_inactive": "拼字: 未开始",
    "status_sprint_active_fmt": "拼字: {} 字",
    "btn_start_sprint": "开始拼字",
    "btn_stop_sprint": "停止拼字",

    "dialog_create_group_title": "创建房间",
    "dialog_group_name_label": "房间名称:",
    "dialog_private_title": "私密房间?",
    "dialog_private_msg": "是否设置为私密房间？",
    "dialog_sprint_title": "开始拼字",
    "dialog_sprint_target": "目标字数:",
    "msg_leave_confirm": "确定要离开房间 [{}] 吗？", # 新增
    "msg_leave_success": "已成功离开房间。", # 新增
    "msg_in_other_room": "你已在另一个房间 (ID: {}) 内，请先离开原房间。", # 优化单人群组错误提示
    "msg_failed": "失败",
    "msg_unknown_err": "未知错误",

    # --- 悬浮窗 ---
    "float_wph": "速度",
    "float_words": "字",
    "float_group_chat": "群聊",
    "float_leaderboard": "行榜",
}