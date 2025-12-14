import streamlit as st
import hashlib
import json
import os
from rights import load_users, save_users, hash_password, check_permission, get_current_user, rerun

def verify_old_password(username, old_password):
    """
    验证原密码是否正确
    
    Args:
        username: 用户名
        old_password: 原密码
        
    Returns:
        bool: 原密码是否正确
    """
    users = load_users()
    if username in users:
        hashed_pwd = users[username]["password"]
        return hashed_pwd == hash_password(old_password)
    return False

def update_password(username, new_password):
    """
    更新用户密码
    
    Args:
        username: 用户名
        new_password: 新密码
        
    Returns:
        bool: 更新是否成功
    """
    users = load_users()
    if username in users:
        users[username]["password"] = hash_password(new_password)
        save_users(users)
        return True
    return False

def change_password_page():
    """
    修改密码页面
    """
    # 检查登录状态
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.error("请先登录")
        rerun()
    
    st.title("修改密码")
    
    # 获取当前用户信息
    current_user = get_current_user()
    if not current_user:
        st.error("用户信息获取失败")
        rerun()
    
    username = current_user["username"]
    
    # 修改密码表单
    with st.form("change_password_form"):
        st.subheader("修改密码")
        
        # 输入原密码
        old_password = st.text_input("原密码", type="password")
        
        # 输入新密码
        new_password = st.text_input("新密码", type="password")
        
        # 确认新密码
        confirm_password = st.text_input("确认新密码", type="password")
        
        # 提交按钮
        submitted = st.form_submit_button("修改密码")
    
    # 表单验证和处理
    if submitted:
        if not old_password.strip():
            st.error("请输入原密码")
        elif not new_password.strip():
            st.error("请输入新密码")
        elif new_password != confirm_password:
            st.error("两次输入的新密码不一致")
        elif new_password.strip() == old_password.strip():
            st.error("新密码不能与原密码相同")
        else:
            # 验证原密码
            if verify_old_password(username, old_password):
                # 更新密码
                if update_password(username, new_password):
                    st.success("密码修改成功，请重新登录")
                    # 清除会话状态，强制用户重新登录
                    for key in list(st.session_state.keys()):
                        if key in ["user", "role", "logged_in", "user_info", "login_time"]:
                            del st.session_state[key]
                    # 重定向到登录页面
                    rerun()
                else:
                    st.error("密码修改失败")
            else:
                st.error("原密码错误")