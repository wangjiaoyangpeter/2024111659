import streamlit as st
import hashlib
import json
import os
from datetime import datetime, timedelta
from streamlit.runtime.scriptrunner import RerunData, RerunException

# 用户数据存储文件
USERS_FILE = "users.json"

# 重新运行应用的函数
def rerun():
    raise RerunException(RerunData())
# 密码加密函数
def hash_password(password):
    """使用SHA-256哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

# 初始化用户数据
def init_users():
    """初始化用户数据文件"""
    default_users = {
        "admin": {
            "password": hash_password("admin123"),
            "role": "admin",
            "name": "系统管理员",
            "department": "管理部",
            "created_at": datetime.now().isoformat()
        },
        "production": {
            "password": hash_password("prod123"),
            "role": "production",
            "name": "生产主管",
            "department": "生产部",
            "created_at": datetime.now().isoformat()
        },
        "inventory": {
            "password": hash_password("inv123"),
            "role": "inventory",
            "name": "库存管理员",
            "department": "库存部",
            "created_at": datetime.now().isoformat()
        }
    }
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, ensure_ascii=False, indent=4)

# 加载用户数据
def load_users():
    """从文件加载用户数据"""
    init_users()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 保存用户数据
def save_users(users):
    """保存用户数据到文件"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# 登录页面
def login_page():
    st.title("员工登录")
    
    # 获取用户输入
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    
    # 提交按钮
    if st.button("登录"):
        users = load_users()
        
        if username in users:
            hashed_pwd = users[username]["password"]
            if hashed_pwd == hash_password(password):
                # 登录成功，保存用户信息到会话状态
                st.session_state.user = username
                st.session_state.role = users[username]["role"]
                st.session_state.logged_in = True
                st.session_state.user_info = {
                    "name": users[username]["name"],
                    "department": users[username]["department"]
                }
                st.session_state.login_time = datetime.now()
                st.success("登录成功！")
                rerun()
            else:
                st.error("密码错误")
        else:
            st.error("用户名不存在")
# 定义角色权限
ROLE_PERMISSIONS = {
    "admin": ["生产计划", "员工管理", "库存管理", "数据看板", "系统设置", "订单管理", "物品管理"],
    "production": ["生产计划", "库存管理", "订单管理"],
    "inventory": ["库存管理", "物品管理"]
}

# 权限检查函数
def check_permission(required_page=None):
    """检查用户是否有访问权限"""
    # 检查是否登录
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.error("请先登录")
        rerun()
    
    # 检查会话是否过期（24小时）
    if (datetime.now() - st.session_state.login_time) > timedelta(hours=24):
        st.error("会话已过期，请重新登录")
        logout()
    
    # 如果指定了页面，检查页面访问权限
    if required_page:
        user_role = st.session_state.role
        if user_role not in ROLE_PERMISSIONS or required_page not in ROLE_PERMISSIONS[user_role]:
            st.error("无权限访问此页面")
            rerun()

# 根据用户角色动态隐藏页面
def hide_unauthorized_pages():
    """根据用户角色隐藏无权限访问的页面"""
    # 在当前实现中，页面隐藏功能已经在main.py中通过导航菜单实现
    # 这里保持函数存在以确保兼容性
    pass

# 登出功能
def logout():
    """用户登出"""
    for key in list(st.session_state.keys()):
        if key in ["user", "role", "logged_in", "user_info", "login_time"]:
            del st.session_state[key]
    st.success("已成功登出")
    rerun()

# 用户管理功能（仅管理员）
def user_management():
    """用户管理页面"""
    check_permission("员工管理")
    
    st.title("员工管理")
    
    users = load_users()
    
    # 显示用户列表
    st.subheader("用户列表")
    for username, user_info in users.items():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
        col1.write(username)
        col2.write(user_info["name"])
        col3.write(user_info["role"])
        col4.write(user_info["department"])
        
        # 删除用户按钮（不能删除管理员自己）
        if username != "admin" and st.session_state.user != username:
            if col5.button("删除", key=f"delete_{username}"):
                del users[username]
                save_users(users)
                st.success(f"用户 {username} 已删除")
                rerun()
    
    # 添加新用户
    st.subheader("添加新用户")
    with st.form("add_user_form"):
        new_username = st.text_input("用户名")
        new_password = st.text_input("密码", type="password")
        new_name = st.text_input("姓名")
        new_role = st.selectbox("角色", ["production", "inventory"])
        new_department = st.text_input("部门")
        
        if st.form_submit_button("添加用户"):
            if new_username in users:
                st.error("用户名已存在")
            else:
                users[new_username] = {
                    "password": hash_password(new_password),
                    "role": new_role,
                    "name": new_name,
                    "department": new_department,
                    "created_at": datetime.now().isoformat()
                }
                save_users(users)
                st.success(f"用户 {new_username} 已添加")
                rerun()

# 系统设置页面（仅管理员）
def system_settings():
    """系统设置页面"""
    check_permission("系统设置")
    
    st.title("系统设置")
    
    # 可以添加系统配置功能，如修改权限规则等
    st.subheader("角色权限配置")
    st.write("当前角色权限配置：")
    for role, pages in ROLE_PERMISSIONS.items():
        st.write(f"{role}: {', '.join(pages)}")

# 获取当前用户信息
def get_current_user():
    """获取当前登录用户信息"""
    if "logged_in" in st.session_state and st.session_state.logged_in:
        return {
            "username": st.session_state.user,
            "role": st.session_state.role,
            "info": st.session_state.user_info,
            "login_time": st.session_state.login_time
        }
    return None

# 在页面顶部显示用户信息
def display_user_info():
    """在页面顶部显示用户信息和登出按钮"""
    user = get_current_user()
    if user:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col2:
            st.write(f"当前用户：{user['info']['name']} ({user['role']})")
        with col3:
            if st.button("登出"):
                logout()
