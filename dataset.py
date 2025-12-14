import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# 数据库文件名
DB_FILE = "factory.db"

class DatabaseManager:
    """数据库管理类，封装数据库操作"""
    
    @staticmethod
    def get_connection():
        """获取数据库连接（单例模式）"""
        if "db_conn" not in st.session_state:
            try:
                conn = sqlite3.connect(DB_FILE, check_same_thread=False)
                conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
                conn.row_factory = sqlite3.Row  # 使查询结果支持字典式访问
                st.session_state.db_conn = conn
            except sqlite3.Error as e:
                st.error(f"数据库连接失败：{e}")
                raise
        return st.session_state.db_conn
    
    @staticmethod
    def close_connection():
        """关闭数据库连接"""
        if "db_conn" in st.session_state:
            try:
                st.session_state.db_conn.close()
                del st.session_state.db_conn
            except sqlite3.Error as e:
                st.error(f"关闭数据库连接失败：{e}")
    
    @staticmethod
    def init_database():
        """初始化数据库表结构"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建物品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    unit TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 创建库存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    current_stock INTEGER NOT NULL DEFAULT 0,
                    min_stock INTEGER NOT NULL DEFAULT 0,
                    max_stock INTEGER NOT NULL DEFAULT 1000,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
                )
            ''')
            
            # 创建订单表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_no TEXT NOT NULL UNIQUE,
                    customer_name TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    delivery_date TEXT,
                    due_date TEXT,
                    processing_time INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_amount REAL NOT NULL DEFAULT 0,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 创建订单详情表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_items (
                    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
                )
            ''')
            
            # 创建用户操作日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operation_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    record_id INTEGER,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 创建设备表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS machines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_name TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT '可用',
                    capacity REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 创建生产计划表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS production_plan (
                    order_id INTEGER NOT NULL,
                    machine_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    PRIMARY KEY (order_id, machine_id),
                    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                    FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            st.error(f"数据库初始化失败：{e}")
            return False
        finally:
            cursor.close()

# 数据加载函数
@st.cache_data(ttl=300)  # 缓存5分钟
def load_items():
    """加载所有物品数据"""
    conn = DatabaseManager.get_connection()
    try:
        df = pd.read_sql("SELECT * FROM items", conn)
        return df
    except sqlite3.Error as e:
        st.error(f"加载物品数据失败：{e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_orders():
    """加载所有订单数据"""
    conn = DatabaseManager.get_connection()
    try:
        df = pd.read_sql("SELECT * FROM orders", conn)
        return df
    except sqlite3.Error as e:
        st.error(f"加载订单数据失败：{e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_inventory():
    """加载所有库存数据"""
    conn = DatabaseManager.get_connection()
    try:
        df = pd.read_sql('''SELECT i.inventory_id, i.item_id, it.item_name, it.description, 
                               it.unit, i.current_stock, i.min_stock, i.max_stock, i.last_updated
                        FROM inventory i
                        JOIN items it ON i.item_id = it.item_id''', conn)
        return df
    except sqlite3.Error as e:
        st.error(f"加载库存数据失败：{e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_order_items(order_id):
    """加载指定订单的详细物品"""
    conn = DatabaseManager.get_connection()
    try:
        df = pd.read_sql('''SELECT oi.*, it.item_name, it.unit 
                        FROM order_items oi
                        JOIN items it ON oi.item_id = it.item_id
                        WHERE oi.order_id = ?''', conn, params=(order_id,))
        return df
    except sqlite3.Error as e:
        st.error(f"加载订单物品失败：{e}")
        return pd.DataFrame()

# 物品管理函数
def add_item(item_name, description, unit, unit_price, created_by):
    """添加新物品"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # 验证物品名称是否已存在
        cursor.execute("SELECT item_id FROM items WHERE item_name = ?", (item_name,))
        if cursor.fetchone():
            st.error("物品名称已存在")
            return False
        
        # 添加物品
        created_at = datetime.now().isoformat()
        cursor.execute(
            '''INSERT INTO items (item_name, description, unit, unit_price, created_at) 
             VALUES (?, ?, ?, ?, ?)''',
            (item_name, description, unit, unit_price, created_at)
        )
        item_id = cursor.lastrowid
        
        # 初始化库存
        cursor.execute(
            '''INSERT INTO inventory (item_id, current_stock, min_stock, max_stock, last_updated) 
             VALUES (?, ?, ?, ?, ?)''',
            (item_id, 0, 0, 1000, created_at)
        )
        
        # 记录操作日志
        cursor.execute(
            '''INSERT INTO operation_logs (user_id, operation_type, table_name, record_id, details, created_at) 
             VALUES (?, ?, ?, ?, ?, ?)''',
            (created_by, "INSERT", "items", item_id, f"添加物品：{item_name}", created_at)
        )
        
        conn.commit()
        st.success("物品添加成功")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"添加物品失败：{e}")
        return False
    finally:
        cursor.close()

# 库存管理函数
def update_inventory(item_id, new_stock, updated_by):
    """更新库存数量"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # 验证库存数量有效性
        if new_stock < 0:
            st.error("库存数量不能为负数")
            return False
        
        last_updated = datetime.now().isoformat()
        
        # 获取当前库存信息
        cursor.execute("SELECT current_stock FROM inventory WHERE item_id = ?", (item_id,))
        current = cursor.fetchone()
        if not current:
            st.error("物品不存在或未初始化库存")
            return False
        
        old_stock = current["current_stock"]
        
        # 更新库存
        cursor.execute(
            "UPDATE inventory SET current_stock = ?, last_updated = ? WHERE item_id = ?",
            (new_stock, last_updated, item_id)
        )
        
        # 记录操作日志
        cursor.execute(
            '''INSERT INTO operation_logs (user_id, operation_type, table_name, record_id, details, created_at) 
             VALUES (?, ?, ?, ?, ?, ?)''',
            (updated_by, "UPDATE", "inventory", item_id, 
             f"库存更新：物品ID {item_id}，从 {old_stock} 到 {new_stock}", last_updated)
        )
        
        conn.commit()
        
        # 检查是否低于最低库存
        cursor.execute("SELECT min_stock FROM inventory WHERE item_id = ?", (item_id,))
        min_stock = cursor.fetchone()["min_stock"]
        if new_stock < min_stock:
            st.warning(f"警告：物品ID {item_id} 的库存已低于最低库存水平 {min_stock}")
        
        st.success("库存更新成功")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"库存更新失败：{e}")
        return False
    finally:
        cursor.close()

def adjust_inventory(item_id, quantity_change, reason, adjusted_by):
    """调整库存数量（增加或减少）"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # 获取当前库存
        cursor.execute("SELECT current_stock FROM inventory WHERE item_id = ?", (item_id,))
        result = cursor.fetchone()
        if not result:
            st.error("物品不存在或未初始化库存")
            return False
        
        current_stock = result["current_stock"]
        new_stock = current_stock + quantity_change
        
        # 验证新库存有效性
        if new_stock < 0:
            st.error("调整后库存数量不能为负数")
            return False
        
        last_updated = datetime.now().isoformat()
        
        # 更新库存
        cursor.execute(
            "UPDATE inventory SET current_stock = ?, last_updated = ? WHERE item_id = ?",
            (new_stock, last_updated, item_id)
        )
        
        # 记录操作日志
        cursor.execute(
            '''INSERT INTO operation_logs (user_id, operation_type, table_name, record_id, details, created_at) 
             VALUES (?, ?, ?, ?, ?, ?)''',
            (adjusted_by, "ADJUST", "inventory", item_id, 
             f"库存调整：物品ID {item_id}，数量变化 {quantity_change}，原因：{reason}", last_updated)
        )
        
        conn.commit()
        st.success(f"库存调整成功：当前库存 {new_stock}")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"库存调整失败：{e}")
        return False
    finally:
        cursor.close()

# 订单管理函数
def create_order(order_no, customer_name, order_date, delivery_date, items, created_by):
    """创建新订单"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # 验证订单号是否已存在
        cursor.execute("SELECT order_id FROM orders WHERE order_no = ?", (order_no,))
        if cursor.fetchone():
            st.error("订单号已存在")
            return False
        
        # 计算订单总金额
        total_amount = sum(item["quantity"] * item["unit_price"] for item in items)
        created_at = datetime.now().isoformat()
        
        # 创建订单
        cursor.execute(
            '''INSERT INTO orders (order_no, customer_name, order_date, delivery_date, status, total_amount, created_by, created_at) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (order_no, customer_name, order_date, delivery_date, "pending", total_amount, created_by, created_at)
        )
        order_id = cursor.lastrowid
        
        # 添加订单物品
        for item in items:
            # 更新库存
            cursor.execute(
                "UPDATE inventory SET current_stock = current_stock - ?, last_updated = ? WHERE item_id = ?",
                (item["quantity"], created_at, item["item_id"])
            )
            
            # 检查库存是否足够
            cursor.execute(
                "SELECT current_stock FROM inventory WHERE item_id = ? AND current_stock < 0",
                (item["item_id"],)
            )
            if cursor.fetchone():
                raise sqlite3.Error(f"物品 {item['item_name']} 库存不足")
            
            # 添加订单物品
            cursor.execute(
            '''INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal) 
             VALUES (?, ?, ?, ?, ?)''',
            (order_id, item["item_id"], item["quantity"], item["unit_price"], 
             item["quantity"] * item["unit_price"])
        )
        
        # 记录操作日志
        cursor.execute(
            '''INSERT INTO operation_logs (user_id, operation_type, table_name, record_id, details, created_at) 
             VALUES (?, ?, ?, ?, ?, ?)''',
            (created_by, "INSERT", "orders", order_id, f"创建订单：{order_no}", created_at)
        )
        
        conn.commit()
        st.success("订单创建成功")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"创建订单失败：{e}")
        return False
    finally:
        cursor.close()

def update_order_status(order_id, new_status, updated_by):
    """更新订单状态"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # 验证状态值
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            st.error(f"无效的订单状态：{new_status}。有效值：{', '.join(valid_statuses)}")
            return False
        
        # 更新订单状态
        updated_at = datetime.now().isoformat()
        cursor.execute(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            (new_status, order_id)
        )
        
        if cursor.rowcount == 0:
            st.error("订单不存在")
            return False
        
        # 记录操作日志
        cursor.execute(
            '''INSERT INTO operation_logs (user_id, operation_type, table_name, record_id, details, created_at) 
             VALUES (?, ?, ?, ?, ?, ?)''',
            (updated_by, "UPDATE", "orders", order_id, f"更新订单状态为：{new_status}", updated_at)
        )
        
        conn.commit()
        st.success("订单状态更新成功")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"更新订单状态失败：{e}")
        return False
    finally:
        cursor.close()

# 数据查询函数
def get_low_stock_items():
    """获取低于最低库存的物品"""
    conn = DatabaseManager.get_connection()
    try:
        df = pd.read_sql('''
            SELECT i.item_id, i.item_name, i.unit, inv.current_stock, inv.min_stock 
             FROM items i
             JOIN inventory inv ON i.item_id = inv.item_id
             WHERE inv.current_stock < inv.min_stock
        ''', conn)
        return df
    except sqlite3.Error as e:
        st.error(f"查询低库存物品失败：{e}")
        return pd.DataFrame()

def get_order_statistics():
    """获取订单统计信息"""
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # 按状态统计订单数量
        cursor.execute('''
            SELECT status, COUNT(*) as count 
             FROM orders 
             GROUP BY status
             ORDER BY status
        ''')
        status_stats = cursor.fetchall()
        
        # 统计总销售额
        cursor.execute('''
            SELECT SUM(total_amount) as total_sales 
             FROM orders 
             WHERE status IN ('shipped', 'delivered')
        ''')
        total_sales = cursor.fetchone()[0] or 0
        
        # 统计待处理订单数量
        cursor.execute('''
            SELECT COUNT(*) as pending_count 
             FROM orders 
             WHERE status = 'pending'
        ''')
        pending_count = cursor.fetchone()[0]
        
        return {
            "status_stats": status_stats,
            "total_sales": total_sales,
            "pending_count": pending_count
        }
    except sqlite3.Error as e:
        st.error(f"获取订单统计失败：{e}")
        return None
    finally:
        cursor.close()