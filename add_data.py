import streamlit as st
import pandas as pd
from datetime import datetime
from rights import check_permission
from dataset import DatabaseManager, load_orders, load_items, add_item

def item_management_page():
    # 权限检查
    check_permission("物品管理")
    
    st.title("物品管理")
    
    # 物品录入表单
    with st.form("add_item_form"):
        st.subheader("添加新物品")
        item_name = st.text_input("物品名称")
        description = st.text_area("物品描述")
        unit = st.selectbox("计量单位", ["个", "件", "箱", "千克", "米", "升", "其他"], index=0)
        unit_price = st.number_input("单价", min_value=0.0, step=0.01)
        
        # 提交按钮
        submitted = st.form_submit_button("添加物品")
    
    # 表单验证
    if submitted:
        if not item_name.strip():
            st.error("物品名称不能为空")
        else:
            # 添加物品
            current_user = st.session_state.get("username", "unknown")
            add_item(item_name, description, unit, unit_price, current_user)
    
    # 物品列表展示
    df_items = load_items()
    if not df_items.empty:
        st.subheader("物品列表")
        st.dataframe(df_items)

def order_management_page():
    # 权限检查
    check_permission("订单管理")
    
    st.title("订单管理")
    
    # 加载物品数据
    df_items = load_items()
    
    # 订单录入表单
    with st.form("add_order_form"):
        st.subheader("添加新订单")
        order_no = st.text_input("订单编号")
        customer_name = st.text_input("客户名称")
        
        if df_items.empty:
            st.error("请先添加物品数据")
        else:
            # 获取物品列表
            items_dict = {row['item_name']: row for _, row in df_items.iterrows()}
            item_options = list(items_dict.keys())
            
            # 选择物品
            selected_item = st.selectbox("选择物品", item_options)
            quantity = st.number_input("数量", min_value=1)
            
            # 计算总价
            if selected_item:
                unit_price = items_dict[selected_item]['unit_price']
                total_price = quantity * unit_price
                st.write(f"单价: {unit_price}，总价: {total_price}")
            
            order_date = st.date_input("订单日期", value=datetime.today())
            delivery_date = st.date_input("交期")
        
        # 提交按钮（在所有情况下都显示）
        submitted = st.form_submit_button("提交订单")
    
    # 表单验证
    if submitted:
        if not order_no.strip() or not customer_name.strip():
            st.error("订单编号和客户名称不能为空")
        elif df_items.empty:
            st.error("请先添加物品数据")
        else:
            # 加载订单数据检查重复
            df_orders = load_orders()
            if not df_orders.empty and order_no in df_orders['order_no'].tolist():
                st.error("订单编号已存在")
            else:
                # 插入新订单
                try:
                    conn = DatabaseManager.get_connection()
                    cursor = conn.cursor()
                    
                    # 获取选中物品的ID和单价
                    item_id = items_dict[selected_item]['item_id']
                    unit_price = items_dict[selected_item]['unit_price']
                    total_amount = quantity * unit_price
                    
                    # 开始事务
                    cursor.execute("BEGIN TRANSACTION")
                    
                    # 插入订单
                    created_at = datetime.now().isoformat()
                    cursor.execute(
                        '''INSERT INTO orders (order_no, customer_name, order_date, delivery_date, 
                        total_amount, created_by, created_at, status) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (order_no, customer_name, order_date.isoformat(), delivery_date.isoformat(), 
                         total_amount, st.session_state.get("username"), created_at, 'pending')
                    )
                    order_id = cursor.lastrowid
                    
                    # 插入订单物品
                    cursor.execute(
                        '''INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal) 
                        VALUES (?, ?, ?, ?, ?)''',
                        (order_id, item_id, quantity, unit_price, total_amount)
                    )
                    
                    # 提交事务
                    cursor.execute("COMMIT")
                    st.success("订单添加成功")
                except Exception as e:
                    # 回滚事务
                    cursor.execute("ROLLBACK")
                    st.error(f"订单添加失败：{e}")
    
    # 订单列表展示
    st.subheader("订单列表")
    df_orders = load_orders()
    if not df_orders.empty:
        # 筛选控件
        status_filter = st.selectbox("按状态筛选", ["全部"] + df_orders["status"].unique().tolist())
        if status_filter != "全部":
            df_orders = df_orders[df_orders["status"] == status_filter]
        
        # 显示订单数据
        st.dataframe(df_orders)
