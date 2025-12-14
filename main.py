import streamlit as st
from rights import hide_unauthorized_pages, display_user_info, login_page
import view
import update
import add_data
import sec
import gen_data

st.set_page_config(page_title="SmartFactory ERP", layout="wide")

# 检查登录状态
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    login_page()
else:
    # 显示用户信息
    display_user_info()
    
    # 隐藏无权限页面
    hide_unauthorized_pages()
    
    # 简单的页面导航示例
    st.sidebar.title("导航菜单")
    pages = ["生产计划", "库存管理", "员工管理", "数据看板"]
    
    # 根据用户角色显示可访问的页面
    user_role = st.session_state.role
    # 所有角色都可以访问修改密码页面
    if user_role == "production":
        pages = ["生产计划", "库存管理", "订单管理", "修改密码"]
    elif user_role == "inventory":
        pages = ["库存管理", "物品管理", "修改密码"]
    elif user_role == "admin":
        pages = ["生产计划", "员工管理", "库存管理", "物品管理", "订单管理", "数据看板", "生成模拟数据", "修改密码"]
    
    selected_page = st.sidebar.radio("选择页面", pages)
    
    # 显示当前页面内容
    st.title(selected_page)
    if selected_page == "生产计划":
        # 调用view.py中的生产计划控制面板
        view.production_plan_page()
    elif selected_page == "库存管理":
        update.inventory_management_page()
    elif selected_page == "员工管理":
        from rights import user_management
        user_management()
    elif selected_page == "数据看板":
        st.write("数据看板页面内容...")
    elif selected_page == "物品管理":
        add_data.item_management_page()
    elif selected_page == "订单管理":
        add_data.order_management_page()
    elif selected_page == "修改密码":
        sec.change_password_page()
    elif selected_page == "生成模拟数据":
        gen_data.gen_data_page()