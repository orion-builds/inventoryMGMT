from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # no colour for some reason
from pydantic import BaseModel # comes with fastapi pip
from typing import Optional
import sqlite3
import math

app = FastAPI()

# 1. Define who is allowed to talk to your API
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# 2. Add the middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Allow our Vue dev server
    allow_credentials=True,
    allow_methods=["*"],               # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],               # Allow all headers
)

# Pydantic data validation for SQLite
class ProductCreate(BaseModel):
    brand: str
    name: str
    amount: float # Maps to REAL in SQLite
    unit_of_measure: str

class InventoryEventCreate(BaseModel):
    product_id: int
    event_type: str         # e.g., "opened", "finished", "restocked"
    event_date: str         # e.g., "2026-03-02"
    cost_sgd: Optional[float] = None
    quantity: int           # e.g., 1 (for one tub) or -1 (if you throw one away)

class CategoryCreate(BaseModel):
    name: str
    ema_alpha: Optional[float] = None # Ranges from 0.0 to 1.0

class RoleCreate(BaseModel):
    name: str
    target_buffer_days: int
    category_id: int
    ema_alpha: Optional[float] = None

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    target_buffer_days: Optional[int] = None
    category_id: Optional[int] = None
    ema_alpha: Optional[float] = None

class RoleHistoryCreate(BaseModel):
    role_id: int
    product_id: int
    start_date: str
    end_date: Optional[str] = None

class RoleHistoryUpdate(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    unit_of_measure: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    ema_alpha: Optional[float] = None

class EventUpdate(BaseModel):
    new_event_type: Optional[str] = None
    new_event_date: Optional[str] = None
    quantity: Optional[int] = None
    cost_sgd: Optional[float] = None

def get_ema_alpha(cursor, role_id, category_id):
    # 1. Check Role level
    cursor.execute("SELECT ema_alpha FROM ROLE WHERE role_id = ?", (role_id,))
    res = cursor.fetchone()
    if res and res[0] is not None: return res[0]

    # 2. Check Category level
    cursor.execute("SELECT ema_alpha FROM CATEGORY WHERE category_id = ?", (category_id,))
    res = cursor.fetchone()
    if res and res[0] is not None: return res[0]

    # 3. Fallback to Global
    cursor.execute("SELECT value FROM SETTINGS WHERE key = 'global_ema_alpha'")
    res = cursor.fetchone()
    return float(res[0]) if res else 0.3

def get_current_ema_for_product(cursor, product_id, role_id, category_id):
    # 1. Fetch historical restocks for this product [cite: 2026-03-03]
    cursor.execute("""
        SELECT cost_sgd, quantity FROM INVENTORY_EVENT 
        WHERE product_id = ? AND event_type LIKE 'Restock%'
        AND cost_sgd IS NOT NULL AND quantity > 0
        ORDER BY event_date ASC
    """, (product_id,))
    restocks = cursor.fetchall()
    
    if not restocks:
        return 0.0

    # 2. Apply the cascade alpha logic [cite: 2026-03-03]
    alpha = get_ema_alpha(cursor, role_id, category_id)
    
    # 3. Calculate EMA [cite: 2026-01-08]
    unit_prices = [r['cost_sgd'] / r['quantity'] for r in restocks]
    ema = unit_prices[0]
    for p in unit_prices[1:]:
        ema = (p * alpha) + (ema * (1 - alpha))
    return ema

def update_learned_habit(cursor, role_id):
    # 1. Fetch current role settings
    cursor.execute("""
        SELECT target_buffer_days, holding_penalty, ema_alpha 
        FROM ROLE 
        WHERE role_id = ?
    """, (role_id,))
    role = cursor.fetchone()
    
    if not role:
        return

    # Default learning rate (alpha) is 0.3 if not overridden
    alpha = role['ema_alpha'] if role['ema_alpha'] is not None else 0.3
    old_buffer = role['target_buffer_days'] if role['target_buffer_days'] is not None else 7
    old_penalty = role['holding_penalty'] if role['holding_penalty'] is not None else 0.002

    # 2. Fetch the most recent restock event for this role to learn from
    cursor.execute("""
        SELECT stock_before_event, implied_h 
        FROM INVENTORY_EVENT 
        WHERE role_id = ? AND event_type LIKE 'Restock%' 
        ORDER BY event_date DESC, event_id DESC LIMIT 1
    """, (role_id,))
    latest_event = cursor.fetchone()
    
    if not latest_event:
        return
        
    new_buffer_rounded = old_buffer
    new_penalty = old_penalty
    
    # 3. Feedback Loop A: Target Buffer
    if latest_event['stock_before_event'] is not None:
        actual_runway = latest_event['stock_before_event']
        # Blend the actual behavior with the old rule
        new_buffer = (alpha * actual_runway) + ((1 - alpha) * old_buffer)
        new_buffer_rounded = max(0, int(round(new_buffer))) # Ensure a clean, positive integer
        
    # 4. Feedback Loop B: Holding Penalty (h)
    if latest_event['implied_h'] is not None:
        # Note: implied_h is stored as a percentage (e.g., 0.5 for 0.5%). 
        # We must divide by 100 to blend it with the decimal holding_penalty (0.005)
        actual_h_decimal = latest_event['implied_h'] / 100.0
        
        # Blend the actual penalty with the old rule
        new_penalty = (alpha * actual_h_decimal) + ((1 - alpha) * old_penalty)
        
        # Guardrail: Keep the penalty within a sane economic range (0.01% to 5% per day)
        new_penalty = max(0.0001, min(new_penalty, 0.05))

    # 5. Commit the updated habits back to the Role
    cursor.execute("""
        UPDATE ROLE 
        SET target_buffer_days = ?,
            holding_penalty = ?
        WHERE role_id = ?
    """, (new_buffer_rounded, new_penalty, role_id))

@app.get("/dashboard/forecast")
def get_restock_forecast():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Fetch Global Settings
        cursor.execute("SELECT value FROM SETTINGS WHERE key = 'default_holding_penalty'")
        setting_res = cursor.fetchone()
        default_h = float(setting_res['value']) if setting_res else 0.015 

        # 2. Get Active Roles
        cursor.execute("""
            SELECT r.role_id, r.name as role_name, r.target_buffer_days, r.category_id, r.holding_penalty,
                   p.product_id, p.brand, p.name as product_name, rh.start_date
            FROM ROLE_HISTORY rh
            JOIN ROLE r ON rh.role_id = r.role_id
            JOIN PRODUCT p ON rh.product_id = p.product_id
            WHERE rh.end_date IS NULL
        """)
        active_roles = [dict(row) for row in cursor.fetchall()]
        
        forecasts = []
        total_daily_burn = 0.0

        for role in active_roles:
            cursor.execute("""
                SELECT event_date, event_type, quantity, cost_sgd 
                FROM INVENTORY_EVENT 
                WHERE product_id = ? AND event_date >= ?
                ORDER BY event_date ASC
            """, (role['product_id'], role['start_date']))
            all_events = [dict(e) for e in cursor.fetchall()]

            # 3. Identify Anchor Point for "Init" cases
            init_event = next((e for e in all_events if e['event_type'] == 'Init'), None)
            anchor_date_str = role['start_date']
            
            if init_event and init_event['quantity'] < 1.0:
                first_finish = next((e for e in all_events if e['event_type'] == 'Finished (-)' and e['event_date'] > init_event['event_date']), None)
                if first_finish:
                    anchor_date_str = first_finish['event_date']

            # 4. History & Current Stock
            history_points = []
            current_stock = 0
            restock_prices = [] 

            for e in all_events:
                if "Restock" in e['event_type'] or e['event_type'] == 'Init': 
                    current_stock += e['quantity']
                    if e['cost_sgd'] and e['quantity'] > 0:
                        restock_prices.append(e['cost_sgd'] / e['quantity'])
                else: 
                    current_stock -= e['quantity']
                
                history_points.append({
                    "date": e['event_date'], 
                    "stock": current_stock, 
                    "event_type": e['event_type']
                })

            # 5. INTERVAL-BASED USAGE MATH
            # Rule: Only count 'Finished' events that occur strictly after our starting anchor
            finished_events = [e for e in all_events if e['event_type'] == 'Finished (-)' and e['event_date'] > anchor_date_str]
            valid_stock = max(0, current_stock) 
            
            # RULE: At least 2 depletions are required to measure a speed interval
            if len(finished_events) >= 2:
                # 1. Calculate individual gaps between depletions [cite: 2026-03-04]
                intervals = []
                for i in range(len(finished_events) - 1):
                    d1 = datetime.strptime(finished_events[i]['event_date'], '%Y-%m-%d')
                    d2 = datetime.strptime(finished_events[i+1]['event_date'], '%Y-%m-%d')
                    intervals.append(max(1, (d2 - d1).days))
                
                mean_int = sum(intervals) / len(intervals)
                burn_rate = 1 / mean_int 

                # 2. Calculate Coefficient of Variation (CV) [cite: 2026-03-04]
                variance = sum((x - mean_int)**2 for x in intervals) / len(intervals)
                std_dev = math.sqrt(variance)
                cv = std_dev / mean_int if mean_int > 0 else 0

                # 3. Stability-Based Confidence Rating [cite: 2026-03-04]
                # Stability improves as CV decreases and sample size increases [cite: 2026-03-04]
                stability_score = cv / math.sqrt(len(intervals))
                if stability_score < 0.05 and len(finished_events) >= 4:
                    conf = "High"
                elif stability_score < 0.15:
                    conf = "Medium"
                else:
                    conf = "Low"
                
                # EMA & WTP Logic
                alpha = get_ema_alpha(cursor, role['role_id'], role['category_id'])
                ema_unit_cost = 0.0
                if restock_prices:
                    ema_unit_cost = restock_prices[0]
                    for p in restock_prices[1:]:
                        ema_unit_cost = (p * alpha) + (ema_unit_cost * (1 - alpha))
                
                daily_cost = burn_rate * ema_unit_cost
                total_daily_burn += daily_cost
                days_remaining = int(valid_stock / burn_rate)
                expected_dt = datetime.now() + timedelta(days=days_remaining)
                
                h_penalty = role['holding_penalty'] if role['holding_penalty'] is not None else default_h
                excess_days = max(0, days_remaining - (role['target_buffer_days'] or 7))
                target_deal = ema_unit_cost * math.pow((1 - h_penalty), excess_days) if excess_days > 0 else ema_unit_cost
                
                forecasts.append({
                    **role, "days_remaining": int(valid_stock / burn_rate),
                    "confidence": conf,
                    "cv": round(cv, 4), # Pass CV to frontend for margin math [cite: 2026-03-04]
                    "intervals_count": len(intervals),
                    "expected_restock": expected_dt.strftime('%Y-%m-%d'),
                    "daily_cost": round(daily_cost, 2), 
                    "stock_on_hand": valid_stock, "history": history_points,
                    "status": "Calculated", "target_deal_price": round(target_deal, 2),
                    "ema_unit_cost": round(ema_unit_cost, 2)
                })
            else:
                # Disqualifies single-event depletions (The Dettol/Whey Fix)
                forecasts.append({
                    **role, "days_remaining": 9999, "daily_cost": 0.0,
                    "status": "Insufficient Data", "confidence": "N/A",
                    "stock_on_hand": valid_stock, "history": history_points,
                    "target_deal_price": 0.0, "ema_unit_cost": 0.0
                })

        forecasts.sort(key=lambda x: x['days_remaining'])
        return {
            "summary": {
                "daily": round(total_daily_burn, 2),
                "monthly": round(total_daily_burn * 30.44, 2),
                "yearly": round(total_daily_burn * 365.25, 2)
            },
            "forecast": forecasts
        }
    finally:
        conn.close()

@app.get("/products/")
def get_products():
    # Connect to the brain
    conn = sqlite3.connect("inventory.db")
    
    # This magic line tells SQLite to return data as dictionaries instead of raw tuples
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    try:
        # The exact same SQL you learn in MySQL Workbench
        cursor.execute("SELECT * FROM PRODUCT")
        
        # Grab every row the database found
        rows = cursor.fetchall()
        
        # Convert those SQLite rows into standard Python dictionaries
        products = [dict(row) for row in rows]
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    # FastAPI will automatically convert this list of dictionaries into a clean JSON response
    return {"inventory": products}

@app.post("/products/")
def create_product(product: ProductCreate):
    # Connect to our local brain
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    try:
        # We use '?' placeholders to prevent SQL Injection attacks
        cursor.execute("""
            INSERT INTO PRODUCT (brand, name, amount, unit_of_measure)
            VALUES (?, ?, ?, ?)
        """, (product.brand, product.name, product.amount, product.unit_of_measure))
        
        # Save the changes
        conn.commit()
        
        # Get the ID of the row we just created
        new_id = cursor.lastrowid
        
    except sqlite3.Error as e:
        # If the database throws an error, tell the web browser
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always close the connection, even if it fails
        conn.close()

    # Return a success message with the new ID
    return {"message": "Product added successfully", "product_id": new_id}

@app.patch("/products/{product_id}")
def update_product(product_id: int, product_data: ProductUpdate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;") # Maintain integrity
    
    try:
        # Dynamically build the SQL update statement
        update_map = product_data.model_dump(exclude_unset=True)
        if not update_map:
            raise HTTPException(status_code=400, detail="No fields provided for update")
            
        set_clause = ", ".join([f"{column} = ?" for column in update_map.keys()])
        params = list(update_map.values())
        params.append(product_id)
        
        query = f"UPDATE PRODUCT SET {set_clause} WHERE product_id = ?"
        cursor.execute(query, params)
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
            
        conn.commit()
        return {"message": "Product updated successfully"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # We turn on Foreign Keys to ensure we don't break database integrity
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # Check if product exists first for a better error message
        cursor.execute("SELECT name FROM PRODUCT WHERE product_id = ?", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Execute the delete
        cursor.execute("DELETE FROM PRODUCT WHERE product_id = ?", (product_id,))
        conn.commit()
        
    except sqlite3.IntegrityError:
        # This happens if a product is currently linked to an Event or Role History
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete product: It is currently linked to inventory events or role history."
        )
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"message": f"Successfully deleted product {product_id}"}

@app.get("/products/with-stock")
def get_products_with_stock():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Calculates real-time stock explicitly for form validation UI
        cursor.execute("""
            SELECT p.*, 
            COALESCE(SUM(CASE WHEN e.event_type IN ('Restock (+)', 'Init') THEN e.quantity ELSE -e.quantity END), 0) as stock_on_hand
            FROM PRODUCT p
            LEFT JOIN INVENTORY_EVENT e ON p.product_id = e.product_id
            GROUP BY p.product_id
        """)
        return {"inventory": [dict(row) for row in cursor.fetchall()]}
    finally:
        conn.close()

# --- GET ALL INVENTORY EVENTS ---
@app.get("/events/")
def get_events():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # We fetch the actual product names so the table is readable
        cursor.execute("""
            SELECT p.brand, p.name, e.*
            FROM INVENTORY_EVENT e
            JOIN PRODUCT p ON e.product_id = p.product_id
            ORDER BY e.event_date DESC
        """)
        
        # FIX: Assign the results to 'rows'
        rows = cursor.fetchall()
        
        # Now 'rows' is defined and can be converted to a list of dicts
        events = [dict(row) for row in rows]
        return {"events": events}
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/events/")
def log_event(event: InventoryEventCreate):
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # 1. Fetch Role, Category, and Target Buffer context 
        # (Updated to also grab r.target_buffer_days in one swift query)
        cursor.execute("""
            SELECT r.role_id, r.category_id, r.target_buffer_days
            FROM ROLE_HISTORY rh
            JOIN ROLE r ON rh.role_id = r.role_id
            WHERE rh.product_id = ? AND rh.end_date IS NULL
        """, (event.product_id,))
        context = cursor.fetchone()
        
        role_id = context['role_id'] if context else None
        category_id = context['category_id'] if context else None
        buffer_days = context['target_buffer_days'] if context and context['target_buffer_days'] is not None else 7

        # --- NEW CONSTRAINT: Prevent Future Dates ---
        from datetime import datetime 
        if datetime.strptime(event.event_date, '%Y-%m-%d').date() > datetime.now().date():
            raise HTTPException(status_code=400, detail="Event date cannot be in the future.")

        # 2. Capture baseline context BEFORE the new event 
        cursor.execute("""
            SELECT SUM(CASE 
                WHEN event_type LIKE 'Restock%' OR event_type = 'Init' THEN quantity 
                ELSE -quantity 
            END) as current_stock
            FROM INVENTORY_EVENT WHERE product_id = ?
        """, (event.product_id,))
        
        res = cursor.fetchone()
        stock_before = res['current_stock'] if res['current_stock'] is not None else 0.0
        
        # --- NEW CONSTRAINT: Prevent over-consumption ---
        if event.event_type == 'Finished (-)' and event.quantity > stock_before:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock. You only have {stock_before} units remaining."
            )
        
        # Calculate EMA baseline using existing cascade rules 
        p_base = 0.0
        if role_id and category_id:
            p_base = get_current_ema_for_product(cursor, event.product_id, role_id, category_id)

        # --- NEW: Calculate Implied Holding Penalty (h) ---
        implied_h = None
        if 'Restock' in event.event_type and event.cost_sgd and event.quantity and p_base > 0:
            p_deal = event.cost_sgd / event.quantity
            excess_days = max(0, stock_before - buffer_days)
            
            # Guardrail: Only calculate if bought early AND at a discount
            if excess_days > 0 and p_deal < p_base:
                # Store it as a percentage to match your frontend formatting
                implied_h = (1 - (p_deal / p_base) ** (1 / excess_days)) * 100

        # 3. Insert the Event with Snapshot (Now including implied_h)
        cursor.execute("""
            INSERT INTO INVENTORY_EVENT 
            (product_id, role_id, event_type, event_date, cost_sgd, quantity, unit_cost, stock_before_event, implied_h)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event.product_id, role_id, event.event_type, event.event_date, 
              event.cost_sgd, event.quantity, p_base, stock_before, implied_h))
        
        # 4. Trigger the Back-Solver Machine Learning 
        if "Restock" in event.event_type and role_id:
            update_learned_habit(cursor, role_id)
        
        conn.commit()
        
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Data integrity error: {str(e)}")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"message": "Inventory event logged and habit updated."}

@app.patch("/events/")
def update_event(product_id: int, event_type: str, event_date: str, event_data: EventUpdate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;") 
    
    try:
        # 1. Build dynamic update fields
        update_fields = []
        params = []

        if event_data.new_event_type is not None:
            update_fields.append("event_type = ?")
            params.append(event_data.new_event_type)
        if event_data.new_event_date is not None:
            update_fields.append("event_date = ?")
            params.append(event_data.new_event_date)
        if event_data.quantity is not None:
            update_fields.append("quantity = ?")
            params.append(event_data.quantity)
        
        # 2. Logic for Restock Price
        # We allow setting cost_sgd, but typically it's NULL for 'Finished' events
        if event_data.cost_sgd is not None:
            update_fields.append("cost_sgd = ?")
            params.append(event_data.cost_sgd)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        # 3. Use the original primary key values for the WHERE clause
        params.extend([product_id, event_type, event_date])
        
        query = f"""
            UPDATE INVENTORY_EVENT 
            SET {', '.join(update_fields)} 
            WHERE product_id = ? AND event_type = ? AND event_date = ?
        """
        
        cursor.execute(query, params)
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Original event not found")
            
        conn.commit()
        return {"message": "Event successfully updated"}
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="An event already exists for this product at that type/time.")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/events/")
def delete_event(product_id: int, event_type: str, event_date: str):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    try:
        # We target the specific composite key combination
        cursor.execute("""
            DELETE FROM INVENTORY_EVENT 
            WHERE product_id = ? AND event_type = ? AND event_date = ?
        """, (product_id, event_type, event_date))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Event not found")
            
        conn.commit()
        return {"message": "Event deleted successfully"}
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/inventory/")
def get_active_inventory():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # We join PRODUCT -> ROLE_HISTORY -> ROLE
        # This ensures we only see items currently 'in use'
        cursor.execute("""
            SELECT 
                p.product_id, 
                p.brand, 
                p.name, 
                r.name as role_name,
                r.target_buffer_days,
                COALESCE(SUM(e.quantity), 0) as current_stock
            FROM PRODUCT p
            JOIN ROLE_HISTORY rh ON p.product_id = rh.product_id
            JOIN ROLE r ON rh.role_id = r.role_id
            LEFT JOIN INVENTORY_EVENT e ON p.product_id = e.product_id
            WHERE rh.end_date IS NULL OR rh.end_date = ''
            GROUP BY p.product_id
        """)
        
        rows = cursor.fetchall()
        active_items = [dict(row) for row in rows]
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"active_inventory": active_items}

@app.get("/inventory/{product_id}")
def get_current_stock(product_id: int):
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # We use SUM() to add up all the quantities for this specific product
        cursor.execute("""
            SELECT SUM(quantity) as current_stock 
            FROM INVENTORY_EVENT 
            WHERE product_id = ?
        """, (product_id,))
        
        result = cursor.fetchone()
        
        # If the result is None, it means no events have been logged yet
        stock = result["current_stock"] if result["current_stock"] is not None else 0
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {
        "product_id": product_id,
        "current_stock": stock
    }

# --- CATEGORY ROUTE ---
@app.get("/categories/")
def get_categories():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    try:
        # Fetching ema_alpha to support the cascade settings lookup
        cursor.execute("SELECT * FROM CATEGORY")
        categories = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"categories": categories}

@app.post("/categories/")
def create_category(category: CategoryCreate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    try:
        # Allowing optional alpha initialization at creation
        cursor.execute("""
            INSERT INTO CATEGORY (name, ema_alpha)
            VALUES (?, ?)
        """, (category.name, category.ema_alpha))
        
        conn.commit()
        new_id = cursor.lastrowid
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"message": "Category added successfully", "category_id": new_id}

@app.patch("/categories/{category_id}")
def update_category(category_id: int, category_data: CategoryUpdate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        # Logic to update only the fields provided in the request body
        update_data = category_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        query = "UPDATE CATEGORY SET "
        params = []
        for key, value in update_data.items():
            query += f"{key} = ?, "
            params.append(value)
        
        query = query.rstrip(", ") + " WHERE category_id = ?"
        params.append(category_id)

        cursor.execute(query, params)
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found")
            
        conn.commit()
        return {"message": "Category updated successfully"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/categories/{category_id}")
def delete_category(category_id: int):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;") 
    
    try:
        cursor.execute("DELETE FROM CATEGORY WHERE category_id = ?", (category_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        conn.commit()
        return {"message": "Category deleted successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Cannot delete category: It is linked to active Roles.")
    finally:
        conn.close()

# --- ROLE ROUTE ---
@app.get("/roles/")
def get_roles():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Fetch ema_alpha so the UI can display current overrides
        cursor.execute("""
            SELECT r.*, c.name as category_name 
            FROM ROLE r
            JOIN CATEGORY c ON r.category_id = c.category_id
        """)
        roles = [dict(row) for row in cursor.fetchall()]
        return {"roles": roles}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/roles/")
def create_role(role: RoleCreate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # Include ema_alpha in the insertion
        cursor.execute("""
            INSERT INTO ROLE (name, target_buffer_days, category_id, ema_alpha)
            VALUES (?, ?, ?, ?)
        """, (role.name, role.target_buffer_days, role.category_id, role.ema_alpha))
        
        conn.commit()
        new_id = cursor.lastrowid
        
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Data integrity error: {str(e)}")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"message": "Role added successfully", "role_id": new_id}

@app.patch("/roles/{role_id}")
def update_role(role_id: int, role_data: RoleUpdate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        update_fields = []
        params = []
        
        # Use exclude_unset=True logic or check fields individually
        if role_data.name is not None:
            update_fields.append("name = ?")
            params.append(role_data.name)
        if role_data.target_buffer_days is not None:
            update_fields.append("target_buffer_days = ?")
            params.append(role_data.target_buffer_days)
        if role_data.category_id is not None:
            update_fields.append("category_id = ?")
            params.append(role_data.category_id)
        if role_data.ema_alpha is not None: # New field logic
            update_fields.append("ema_alpha = ?")
            params.append(role_data.ema_alpha)
            
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided for update")
            
        params.append(role_id)
        query = f"UPDATE ROLE SET {', '.join(update_fields)} WHERE role_id = ?"
        
        cursor.execute(query, params)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Role not found")
            
        conn.commit()
        return {"message": "Role updated successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Invalid category_id provided")
    finally:
        conn.close()

@app.delete("/roles/{role_id}")
def delete_role(role_id: int):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    # Critical for enforcing the "Safety Lock"
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        cursor.execute("DELETE FROM ROLE WHERE role_id = ?", (role_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Role not found")
            
        conn.commit()
        return {"message": "Role definition deleted successfully"}
        
    except sqlite3.IntegrityError:
        # This triggers if there are entries in ROLE_HISTORY for this role
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete role: It is currently linked to routine history. Delete history entries first."
        )
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- GET ALL ROLE HISTORY ---
@app.get("/role-history/")
def get_role_history():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # We JOIN with PRODUCT to get names instead of just IDs
        cursor.execute("""
            SELECT rh.*, p.brand, p.name as product_name
            FROM ROLE_HISTORY rh
            JOIN PRODUCT p ON rh.product_id = p.product_id
            ORDER BY rh.start_date DESC
        """)
        history = [dict(row) for row in cursor.fetchall()]
        return {"role_history": history}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/role-history/")
def create_role_history(history: RoleHistoryCreate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # Enforce foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # 1. AUTO-TERMINATE: Update the previous active product for this role
        # We set its end_date to the start_date of the new product
        cursor.execute("""
            UPDATE ROLE_HISTORY 
            SET end_date = ? 
            WHERE role_id = ? AND end_date IS NULL
        """, (history.start_date, history.role_id))

        # 2. INSERT: Log the new product assignment
        cursor.execute("""
            INSERT INTO ROLE_HISTORY (role_id, product_id, start_date, end_date)
            VALUES (?, ?, ?, ?)
        """, (history.role_id, history.product_id, history.start_date, history.end_date))
        
        conn.commit()
        return {"message": "Product swapped successfully; previous assignment terminated."}
        
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Data integrity error: {str(e)}")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.patch("/role-history/")
def update_role_history(role_id: int, product_id: int, start_date: str, update: RoleHistoryUpdate):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        # We use the original 'start_date' from the URL to find the row,
        # then update it with the new values from the body.
        cursor.execute("""
            UPDATE ROLE_HISTORY 
            SET start_date = COALESCE(?, start_date), 
                end_date = ? 
            WHERE role_id = ? AND product_id = ? AND start_date = ?
        """, (update.start_date, update.end_date, role_id, product_id, start_date))
        conn.commit()
        return {"message": "History updated successfully."}
    finally:
        conn.close()

@app.delete("/role-history/")
def delete_role_history(role_id: int, product_id: int, start_date: str):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM ROLE_HISTORY 
            WHERE role_id = ? AND product_id = ? AND start_date = ?
        """, (role_id, product_id, start_date))
        conn.commit()
        return {"message": "Assignment deleted."}
    finally:
        conn.close()

@app.get("/settings/")
def get_settings():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM SETTINGS")
    # Convert list of rows to a simple key-value dictionary
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings

@app.patch("/settings/{key}")
def update_setting(key: str, value: str):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE SETTINGS SET value = ? WHERE key = ?", (value, key))
    if cursor.rowcount == 0:
        # If the key doesn't exist yet, insert it [cite: 2026-03-03]
        cursor.execute("INSERT INTO SETTINGS (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return {"message": f"Setting '{key}' updated successfully"}