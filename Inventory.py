from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import pandas as pd
from dataset import DatabaseManager
import streamlit as st
from rights import check_permission
import plotly.express as px
def predict_inventory(alpha=0.2):
    """使用指数平滑法预测库存需求"""
    try:
        # 加载库存数据
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        # 获取历史库存数据
        cursor.execute(
        "SELECT date, sales FROM inventory_history ORDER BY date"
        )
        rows = cursor.fetchall()
        # 转换为DataFrame
        data = pd.DataFrame(rows, columns=["date", "sales"])
        data["date"] = pd.to_datetime(data["date"])
        data.set_index("date", inplace=True)
        # 检查数据是否足够
        if len(data) < 2:
            return None
        # 创建模型并拟合
        model = SimpleExpSmoothing(data["sales"])
        model_fit = model.fit(smoothing_level=alpha)
        # 预测未来30天的需求
        forecast = model_fit.forecast(steps=30)
        return forecast.values.tolist()
    except Exception as e:
        st.error(f"库存预测失败：{e}")
        return None
def load_inventory():
    """加载库存数据"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        # 获取当前库存数据
        cursor.execute("SELECT * FROM inventory")
        rows = cursor.fetchall()
        
        # 获取库存历史数据
        cursor.execute("SELECT * FROM inventory_history ORDER BY date")
        history_rows = cursor.fetchall()
        
        # 转换为DataFrame
        df = pd.DataFrame(history_rows, columns=["id", "item_id", "date", "sales", "current_stock", "safety_stock"])
        df["date"] = pd.to_datetime(df["date"])
        
        return df
    except Exception as e:
        st.error(f"加载库存数据失败：{e}")
        return None

def inventory_management_page():
    # 权限检查
    check_permission("库存管理")
    
    # 侧边栏参数设置
    with st.sidebar:
        st.title("库存预测设置")
        alpha = st.slider("平滑系数", 0.0, 1.0, 0.2)
        days_to_predict = st.slider("预测天数", 7, 90, 30)
        if st.button("重新计算预测"):
            st.rerun()
    
    # 加载库存数据
    df_inventory = load_inventory()
    
    if df_inventory is not None and not df_inventory.empty:
        # 预测库存需求
        forecast = predict_inventory(alpha=alpha)
        
        if forecast is not None:
            # 创建预测数据DataFrame
            dates = pd.date_range(start=df_inventory["date"].max(), periods=days_to_predict+1)[1:]
            df_forecast = pd.DataFrame({
                "date": dates,
                "sales": forecast[:days_to_predict]
            })
            
            # 合并历史和预测数据
            df_combined = pd.concat([df_inventory, df_forecast])
            
            # 创建库存趋势图
            fig = px.line(df_combined, x="date", y="sales", title="库存趋势预测")
            
            # 添加安全库存线
            if "safety_stock" in df_inventory.columns:
                safety_stock = df_inventory["safety_stock"].mean()
                fig.add_hline(
                    y=safety_stock,
                    line_dash="dash",
                    line_color="red",
                    name="安全库存"
                )
            
            # 显示图表
            st.plotly_chart(fig)
        
        # 库存预警
        st.subheader("库存预警")
        # 获取当前库存状态
        conn = DatabaseManager.get_connection()
        df_current_inventory = pd.read_sql("SELECT * FROM inventory", conn)
        
        if not df_current_inventory.empty and "safety_stock" in df_current_inventory.columns:
            warning_count = 0
            for _, row in df_current_inventory.iterrows():
                if row["current_stock"] < row["safety_stock"]:
                    st.warning(f"警告：{row['item_name']}库存({row['current_stock']})低于安全库存({row['safety_stock']})！")
                    warning_count += 1
            
            if warning_count == 0:
                st.success("所有商品库存均高于安全库存！")
        else:
            st.info("没有库存数据或未设置安全库存。")
    else:
        st.info("没有库存历史数据可显示。")