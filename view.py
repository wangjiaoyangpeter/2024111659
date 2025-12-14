import plotly.express as px
from st_pages import Page, add_page_title
import streamlit as st
from rights import check_permission
from dataset import DatabaseManager
import pandas as pd
from datetime import datetime
from Inventory import predict_inventory

# 加载生产计划数据
def loadProductionPlan():
    conn = DatabaseManager.get_connection()
    df = pd.read_sql(
    "SELECT order_id, machine_id, start_time, end_time FROM production_plan",
    conn
    )
    return df
# 甘特图生成
def show_gantt():
    df = loadProductionPlan()
    # 转换为Plotly甘特图所需格式
    df_gantt = df.copy()
    df_gantt["Task"] = df_gantt["order_id"].astype(str)
    df_gantt["Resource"] = df_gantt["machine_id"].astype(str)
    # 创建甘特图
    fig = px.timeline(
    df_gantt,
    x_start="start_time",
    x_end="end_time",
    y="Resource",
    color="Task",
    hover_name="Task"
    )
    # 翻转y轴，使设备显示顺序合理
    fig.update_yaxes(autorange="reversed")
    # 设置图表标题和布局
    fig.update_layout(
    title="生产计划甘特图",
    xaxis_title="时间",
    yaxis_title="设备",
    height=600
    )
    # 显示图表
    st.plotly_chart(fig)
# 生产计划优化算法
def optimizeProductionPlan(num_orders_to_process=5):
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    # 获取待处理订单
    cursor.execute("SELECT * FROM orders WHERE status = '待处理'")
    orders = cursor.fetchall()
    # 获取可用设备
    cursor.execute("SELECT * FROM machines WHERE status = '可用'")
    machines = cursor.fetchall()
    # 计算订单优先级并排序
    for order in orders:
        # 计算优先级（示例代码，具体逻辑根据需求调整）
        days_remaining = (order["due_date"] - datetime.now()).days
        processing_days = order["processing_time"]
        critical_ratio = days_remaining / processing_days if processing_days != 0 else 0
        priority = 0.4 * (1 / (critical_ratio + 1)) + \
                  0.3 * (1 / (processing_days + 1)) + \
                  0.3 * (1 / (days_remaining + 1))
        # 更新订单优先级
        cursor.execute(
            "UPDATE orders SET priority = ? WHERE id = ?",
            (priority, order["id"])
        )
    # 按优先级排序订单
    cursor.execute("""UPDATE orders SET status = '生产中' 
    WHERE id IN (SELECT id FROM (SELECT * FROM orders
    WHERE status = '待处理' ORDER BY priority LIMIT
    ?))""", (num_orders_to_process,))
    conn.commit()

def production_plan_page():
    # 权限检查
    check_permission("生产计划")
    # 侧边栏控件
    with st.sidebar:
        st.title("生产计划控制台")
        num_orders = st.slider("每次排产订单数", 1, 10, 5)
        if st.button("重新排产"):
            optimizeProductionPlan(num_orders)
            st.rerun()
    # 显示甘特图
    show_gantt()
    # 生产计划表展示
    df_plan = loadProductionPlan()
    # 将字符串转换为datetime对象
    df_plan['start_time'] = pd.to_datetime(df_plan['start_time'])
    df_plan['end_time'] = pd.to_datetime(df_plan['end_time'])
    st.dataframe(df_plan.style.format({"start_time": "{:%Y-%m-%d %H:%M}", "end_time": "{:%Y-%m-%d %H:%M}"}))


