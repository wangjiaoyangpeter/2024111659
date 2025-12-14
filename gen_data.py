import streamlit as st
import random
import sqlite3
from datetime import datetime, timedelta
from dataset import DatabaseManager, add_item, create_order
import string

# 连接到数据库
conn = DatabaseManager.get_connection()
cursor = conn.cursor()

# 生成随机字符串的函数
def random_string(length=10):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# 生成随机物品数据
def generate_items(num_items=20):
    """生成随机物品数据"""
    item_names = [
        "螺丝", "螺母", "垫片", "轴承", "齿轮", "弹簧", "扳手", "钳子",
        "螺丝刀", "锤子", "钻头", "锯条", "刀片", "链条", "皮带", "轴承座",
        "联轴器", "密封件", "润滑油", "液压油", "电机", "泵", "阀门", "管道",
        "传感器", "控制器", "开关", "按钮", "指示灯", "继电器"
    ]
    
    units = ["个", "件", "箱", "千克", "米", "升", "套", "组"]
    
    created_at = datetime.now().isoformat()
    created_by = "admin"
    
    # 如果提供的物品名称不够，随机生成
    while len(item_names) < num_items:
        item_names.append(f"物品{random_string(5)}")
    
    count = 0
    for i in range(num_items):
        item_name = item_names[i]
        description = f"{item_name} - 描述信息"
        unit = random.choice(units)
        unit_price = round(random.uniform(1.0, 1000.0), 2)
        
        # 检查物品是否已存在
        cursor.execute("SELECT item_id FROM items WHERE item_name = ?", (item_name,))
        if not cursor.fetchone():
            try:
                # 使用现有的add_item函数添加物品
                if add_item(item_name, description, unit, unit_price, created_by):
                    count += 1
            except Exception as e:
                st.error(f"添加物品 {item_name} 失败: {e}")
    
    return count

# 生成随机库存数据
def generate_inventory(min_stock=10, max_stock=1000):
    """为所有物品生成随机库存数据"""
    try:
        # 获取所有物品ID
        cursor.execute("SELECT item_id FROM items")
        items = cursor.fetchall()
        
        count = 0
        for item in items:
            item_id = item[0]
            current_stock = random.randint(0, max_stock)
            min_stock = random.randint(0, 50)
            max_stock = random.randint(100, 1000)
            last_updated = datetime.now().isoformat()
            
            # 更新库存
            cursor.execute(
                "UPDATE inventory SET current_stock = ?, min_stock = ?, max_stock = ?, last_updated = ? WHERE item_id = ?",
                (current_stock, min_stock, max_stock, last_updated, item_id)
            )
            count += 1
        
        conn.commit()
        return count
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"生成库存数据失败: {e}")
        return 0

# 生成随机客户名称
def generate_customer_names(num=50):
    """生成随机客户名称"""
    customer_names = [
        "张三机械有限公司", "李四自动化设备厂", "王五精密仪器厂", "赵六电气科技公司",
        "孙七模具制造有限公司", "周八五金制品厂", "吴九汽车零部件公司", "郑十电子科技有限公司",
        "冯十一重型机械有限公司", "陈十二液压设备厂", "褚十三气动元件公司", "卫十四自动化控制系统",
        "蒋十五工业设备有限公司", "沈十六金属制品厂", "韩十七机械加工厂", "杨十八机械设备有限公司",
        "朱十九工业自动化公司", "秦二十精密机械有限公司"
    ]
    
    # 如果提供的客户名称不够，随机生成
    while len(customer_names) < num:
        customer_names.append(f"{random_string(2)}客户{random_string(5)}")
    
    return customer_names

# 生成随机订单数据
def generate_orders(num_orders=30):
    """生成随机订单数据"""
    try:
        # 获取所有物品
        cursor.execute("SELECT item_id, item_name, unit_price FROM items")
        items = cursor.fetchall()
        
        if not items:
            st.error("请先生成物品数据")
            return 0
        
        customer_names = generate_customer_names()
        created_by = "admin"
        
        count = 0
        for i in range(num_orders):
            # 生成唯一的订单号
            while True:
                order_no = f"ORD-{random_string(8)}"
                cursor.execute("SELECT order_id FROM orders WHERE order_no = ?", (order_no,))
                if not cursor.fetchone():
                    break
            
            customer_name = random.choice(customer_names)
            
            # 生成随机日期（过去3个月内）
            days_ago = random.randint(0, 90)
            order_date = datetime.now() - timedelta(days=days_ago)
            
            # 交期（订单日期后1-15天）
            delivery_days = random.randint(1, 15)
            delivery_date = order_date + timedelta(days=delivery_days)
            
            # 选择随机物品
            selected_items = []
            num_order_items = random.randint(1, 5)
            
            for _ in range(num_order_items):
                item = random.choice(items)
                item_id, item_name, unit_price = item
                quantity = random.randint(1, 100)
                
                selected_items.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "quantity": quantity,
                    "unit_price": unit_price
                })
            
            # 创建订单
            if create_order(order_no, customer_name, order_date.isoformat(), delivery_date.isoformat(), selected_items, created_by):
                count += 1
        
        return count
    except Exception as e:
        conn.rollback()
        st.error(f"生成订单数据失败: {e}")
        return 0

# 更新订单状态
def update_order_statuses():
    """随机更新订单状态"""
    try:
        statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        
        # 获取所有订单ID
        cursor.execute("SELECT order_id FROM orders")
        orders = cursor.fetchall()
        
        count = 0
        for order in orders:
            order_id = order[0]
            status = random.choice(statuses)
            
            cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
            count += 1
        
        conn.commit()
        return count
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"更新订单状态失败: {e}")
        return 0

# 生成随机设备数据
def generate_machines(num_machines=15):
    """生成随机设备数据"""
    machine_types = ["车床", "铣床", "磨床", "钻床", "镗床", "冲床", "剪板机", "折弯机"]
    statuses = ["可用", "维修中", "停用"]
    
    created_at = datetime.now().isoformat()
    
    try:
        count = 0
        for i in range(num_machines):
            machine_name = f"{random.choice(machine_types)}-{random_string(4)}"
            status = random.choice(statuses)
            capacity = round(random.uniform(100.0, 1000.0), 2)
            
            # 检查设备是否已存在
            cursor.execute("SELECT id FROM machines WHERE machine_name = ?", (machine_name,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO machines (machine_name, status, capacity, created_at) VALUES (?, ?, ?, ?)",
                    (machine_name, status, capacity, created_at)
                )
                count += 1
        
        conn.commit()
        return count
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"生成设备数据失败: {e}")
        return 0

# 生成生产计划数据
def generate_production_plans():
    """生成生产计划数据"""
    try:
        # 获取所有订单ID和设备ID
        cursor.execute("SELECT order_id FROM orders WHERE status IN ('pending', 'processing')")
        orders = cursor.fetchall()
        
        cursor.execute("SELECT id FROM machines WHERE status = '可用'")
        machines = cursor.fetchall()
        
        if not orders or not machines:
            st.error("没有待处理订单或可用设备")
            return 0
        
        count = 0
        for order in orders:
            order_id = order[0]
            machine = random.choice(machines)
            machine_id = machine[0]
            
            # 生成随机时间
            start_time = datetime.now() + timedelta(hours=random.randint(0, 48))
            end_time = start_time + timedelta(hours=random.randint(1, 24))
            
            try:
                cursor.execute(
                    "INSERT INTO production_plan (order_id, machine_id, start_time, end_time) VALUES (?, ?, ?, ?)",
                    (order_id, machine_id, start_time.isoformat(), end_time.isoformat())
                )
                count += 1
            except sqlite3.IntegrityError:
                # 如果已存在，则跳过
                continue
        
        conn.commit()
        return count
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"生成生产计划失败: {e}")
        return 0

# 生成所有模拟数据的函数
def generate_all_data(items=20, inventories=True, orders=30, machines=15, production_plans=True):
    """生成所有模拟数据"""
    st.write("开始生成模拟数据...")
    
    # 生成物品
    item_count = generate_items(items)
    st.write(f"生成了 {item_count} 条物品数据")
    
    # 生成库存
    if inventories and item_count > 0:
        inventory_count = generate_inventory()
        st.write(f"生成了 {inventory_count} 条库存数据")
    
    # 生成订单
    if orders > 0:
        order_count = generate_orders(orders)
        st.write(f"生成了 {order_count} 条订单数据")
    
    # 更新订单状态
    if orders > 0:
        status_count = update_order_statuses()
        st.write(f"更新了 {status_count} 条订单状态")
    
    # 生成设备
    if machines > 0:
        machine_count = generate_machines(machines)
        st.write(f"生成了 {machine_count} 条设备数据")
    
    # 生成生产计划
    if production_plans and orders > 0 and machines > 0:
        plan_count = generate_production_plans()
        st.write(f"生成了 {plan_count} 条生产计划数据")
    
    st.success("所有模拟数据生成完成！")

# 模拟数据页面
def gen_data_page():
    """模拟数据生成页面"""
    st.title("生成模拟数据")
    st.write("该功能用于生成演示数据，包括物品、库存、订单、设备和生产计划等。")
    
    # 生成数据的选项
    with st.form("gen_data_form"):
        st.subheader("数据生成选项")
        
        num_items = st.number_input("物品数量", min_value=5, max_value=100, value=20)
        num_orders = st.number_input("订单数量", min_value=5, max_value=200, value=30)
        num_machines = st.number_input("设备数量", min_value=3, max_value=50, value=15)
        
        include_production_plans = st.checkbox("生成生产计划", value=True)
        
        submitted = st.form_submit_button("开始生成数据")
    
    # 生成数据
    if submitted:
        generate_all_data(
            items=num_items,
            orders=num_orders,
            machines=num_machines,
            production_plans=include_production_plans
        )

if __name__ == "__main__":
    gen_data_page()