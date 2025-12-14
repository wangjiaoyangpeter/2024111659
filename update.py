import pandas as pd
import streamlit as st
import st_aggrid
import plotly.express as px
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from dataset import DatabaseManager
from rights import check_permission
from datetime import datetime

# 添加日志记录功能
def log_action(user, operation_type, table_name, record_id, details):
    """记录操作日志"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO operation_logs (user_id, operation_type, table_name, record_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user, operation_type, table_name, record_id, details, created_at)
        )
        conn.commit()
    except Exception as e:
        print(f"日志记录失败：{e}")  # 使用print而非st.error，避免干扰用户界面

# 添加数据验证功能
def validate_inventory_data(df):
    """验证库存数据"""
    errors = []
    
    # 检查数值列是否为正数
    numeric_columns = ["current_stock", "min_stock", "max_stock"]
    for col in numeric_columns:
        if col in df.columns:
            if not (df[col] >= 0).all():
                errors.append(f"{col}必须为非负数")
    
    # 检查最大库存是否大于最小库存
    if "max_stock" in df.columns and "min_stock" in df.columns:
        if not (df["max_stock"] >= df["min_stock"]).all():
            errors.append("最大库存必须大于等于最小库存")
    
    return errors

# 添加库存预警功能
def check_inventory_alerts(df):
    """检查库存预警"""
    alerts = []
    if "current_stock" in df.columns and "min_stock" in df.columns:
        for _, row in df.iterrows():
            if row["current_stock"] < row["min_stock"]:
                alerts.append({
                    "item_name": row.get("item_name", "未知商品"),
                    "current_stock": row["current_stock"],
                    "min_stock": row["min_stock"],
                    "max_stock": row.get("max_stock", 0),
                    "alert_type": "低库存警告"
                })
    return alerts

# 添加库存可视化功能
def visualize_inventory(df):
    """可视化库存数据"""
    if df.empty:
        return
    
    # 库存状态分布饼图
    if "category" in df.columns:
        fig = px.pie(df, values="current_stock", names="category", title="库存分类分布")
        st.plotly_chart(fig)
    
    # 库存水平条形图
    fig = px.bar(df, x="current_stock", y="item_name", orientation='h', title="各商品库存水平")
    fig.add_hline(y=df["min_stock"].mean(), line_dash="dash", line_color="red", name="平均最低库存")
    st.plotly_chart(fig)

# 改进后的库存加载功能
def load_inventory():
    """加载库存数据"""
    try:
        conn = DatabaseManager.get_connection()
        # 连接inventory和items表获取完整信息
        df_inventory = pd.read_sql('''
            SELECT inv.*, it.item_name, it.description, it.unit
            FROM inventory inv
            JOIN items it ON inv.item_id = it.item_id
        ''', conn)
        
        # 确保数值列的类型正确
        numeric_columns = ["current_stock", "min_stock", "max_stock"]
        for col in numeric_columns:
            if col in df_inventory.columns:
                df_inventory[col] = pd.to_numeric(df_inventory[col], errors="coerce")
        
        return df_inventory
    except Exception as e:
        st.error(f"加载库存数据失败：{e}")
        return pd.DataFrame()

def inventory_management_page():
    """库存管理页面"""
    # 权限检查
    check_permission("库存管理")
    
    st.title("库存管理")
    
    # 获取当前用户信息
    current_user = st.session_state.get("username", "unknown")
    
    # 获取库存数据
    df_inventory = load_inventory()
    
    if df_inventory.empty:
        st.info("暂无库存数据")
        return
    
    # 显示库存预警
    alerts = check_inventory_alerts(df_inventory)
    if alerts:
        with st.expander("库存预警", expanded=True):
            for alert in alerts:
                color = "🔴" if alert["alert_type"] == "紧急补货" else "🟡"
                st.warning(f"{color} {alert['alert_type']}: {alert['item_name']} 库存({alert['current_stock']})低于最低库存({alert['min_stock']})！")
    else:
        st.success("✅ 所有商品库存状态正常")
    
    # 配置表格选项
    gb = GridOptionsBuilder.from_dataframe(df_inventory)
    
    # 设置列配置
    gb.configure_default_column(editable=True, resizable=True, filterable=True, sortable=True)
    gb.configure_column("inventory_id", editable=False, sortable=True, filterable=True)
    gb.configure_column("item_id", editable=False, sortable=True, filterable=True)
    gb.configure_column("item_name", type="stringColumn", editable=False, sortable=True, filterable=True)
    gb.configure_column("description", type="stringColumn", editable=False, sortable=True, filterable=True)
    gb.configure_column("unit", type="stringColumn", editable=False, sortable=True, filterable=True)
    gb.configure_column("current_stock", type="numericColumn", editable=True, sortable=True, filterable=True, precision=0)
    gb.configure_column("min_stock", type="numericColumn", editable=True, sortable=True, filterable=True, precision=0)
    gb.configure_column("max_stock", type="numericColumn", editable=True, sortable=True, filterable=True, precision=0)
    
    # 设置选择模式
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    
    # 设置其他选项
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    
    # 构建表格配置
    gridOptions = gb.build()
    
    # 显示表格
    st.write("当前库存状态")
    grid_response = AgGrid(
        df_inventory,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True,
        height=400,
        width='100%',
        theme='streamlit'
    )
    
    # 获取更新后的数据
    updated_df = pd.DataFrame(grid_response['data'])
    
    # 检查数据是否发生变化
    if not updated_df.equals(df_inventory):
        # 验证数据
        validation_errors = validate_inventory_data(updated_df)
        
        if validation_errors:
            st.error("数据验证失败：")
            for error in validation_errors:
                st.error(f"- {error}")
        else:
            try:
                # 更新数据库
                conn = DatabaseManager.get_connection()
                cursor = conn.cursor()
                
                # 开始事务
                cursor.execute("BEGIN TRANSACTION")
                
                # 遍历更新每一行
                for _, row in updated_df.iterrows():
                    # 只更新实际变化的行
                    original_row = df_inventory[df_inventory["inventory_id"] == row["inventory_id"]]
                    if not original_row.empty:
                        cursor.execute(
                            "UPDATE inventory SET current_stock = ?, min_stock = ?, max_stock = ?, last_updated = ? WHERE inventory_id = ?",
                            (
                                row["current_stock"], 
                                row["min_stock"], 
                                row["max_stock"],
                                datetime.now().isoformat(),
                                row["inventory_id"]
                            )
                        )
                
                # 提交事务
                conn.commit()
                
                # 记录操作日志
                log_action(current_user, "UPDATE", "inventory", None, f"更新了{len(updated_df)}条库存记录")
                
                st.success("库存数据已更新")
                
                # 刷新数据
                df_inventory = updated_df
                
            except Exception as e:
                # 回滚事务
                conn.rollback()
                st.error(f"库存更新失败：{e}")
                log_action(current_user, "UPDATE", "inventory", None, f"更新失败：{str(e)}")
            finally:
                cursor.close()
    
    # 显示库存可视化
    with st.expander("库存可视化", expanded=False):
        visualize_inventory(df_inventory)
    
    # 显示批量操作选项
    with st.expander("批量操作", expanded=False):
        selected_rows = grid_response['selected_rows']
        if selected_rows:
            df_selected = pd.DataFrame(selected_rows)
            st.write(f"已选择 {len(df_selected)} 条记录")
            
            # 批量调整库存
            batch_adjustment = st.number_input("批量调整库存数量", value=0)
            if st.button("应用批量调整"):
                try:
                    conn = DatabaseManager.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("BEGIN TRANSACTION")
                    
                    updated_count = 0
                    for _, row in df_selected.iterrows():
                        new_stock = row["current_stock"] + batch_adjustment
                        if new_stock >= 0:  # 确保库存不为负
                            cursor.execute(
                                "UPDATE inventory SET current_stock = ?, last_updated = ? WHERE inventory_id = ?",
                                (
                                    new_stock,
                                    datetime.now().isoformat(),
                                    row["inventory_id"]
                                )
                            )
                            updated_count += 1
                    
                    conn.commit()
                    log_action(current_user, "UPDATE", "inventory", None, f"批量调整了{updated_count}条记录，每条{batch_adjustment}")
                    st.success("批量调整已完成")
                    # 刷新页面
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"批量调整失败：{e}")
                    log_action(current_user, "UPDATE", "inventory", None, f"批量调整失败：{str(e)}")
                finally:
                    cursor.close()