from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # no colour for some reason
from pydantic import BaseModel # comes with fastapi pip
from typing import Optional
import sqlite3

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

class RoleCreate(BaseModel):
    name: str
    target_buffer_days: int
    category_id: int

class RoleHistoryCreate(BaseModel):
    role_id: int
    product_id: int
    start_date: str
    end_date: Optional[str] = None

class RoleHistoryUpdate(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    target_buffer_days: Optional[int] = None
    category_id: Optional[int] = None

class EventUpdate(BaseModel):
    quantity: Optional[int] = None
    cost_sgd: Optional[float] = None

class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    unit_of_measure: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None



@app.get("/dashboard/forecast")
def get_restock_forecast():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Get Active Roles
        cursor.execute("""
            SELECT r.role_id, r.name as role_name, r.target_buffer_days,
                   p.product_id, p.brand, p.name as product_name, rh.start_date
            FROM ROLE_HISTORY rh
            JOIN ROLE r ON rh.role_id = r.role_id
            JOIN PRODUCT p ON rh.product_id = p.product_id
            WHERE rh.end_date IS NULL
        """)
        active_roles = [dict(row) for row in cursor.fetchall()]
        
        forecasts = []
        for role in active_roles:
            # 2. FILTER BY ERA: Fetch events from current era start to prevent legacy data errors
            cursor.execute("""
                SELECT event_date, event_type, quantity 
                FROM INVENTORY_EVENT 
                WHERE product_id = ? AND event_date >= ?
                ORDER BY event_date ASC
            """, (role['product_id'], role['start_date']))
            events = cursor.fetchall()

            history_points = []
            current_stock = 0
            for e in events:
                if "Restock" in e['event_type']: 
                    current_stock += e['quantity']
                else: 
                    current_stock -= e['quantity']
                history_points.append({"date": e['event_date'], "stock": current_stock, "event_type": e['event_type']})

            # 3. Consumption Math & Confidence Logic
            cursor.execute("""
                SELECT MIN(event_date) as first_use, COUNT(*) as units_finished
                FROM INVENTORY_EVENT 
                WHERE product_id = ? AND event_type = 'Finished (-)' AND event_date >= ?
            """, (role['product_id'], role['start_date']))
            usage = cursor.fetchone()
            
            valid_stock = max(0, current_stock) 
            units = usage['units_finished'] if usage['units_finished'] else 0
            
            if units >= 1 and usage['first_use']:
                # Confidence Ranking based on sample size
                if units >= 3:
                    conf = "High"
                    error_margin = 0.10  # 10% variance
                elif units == 2:
                    conf = "Medium"
                    error_margin = 0.25  # 25% variance
                else:
                    conf = "Low"
                    error_margin = 0.45  # 45% variance

                # Core Forecast Calculation
                first_dt = datetime.strptime(usage['first_use'], '%Y-%m-%d')
                total_days = max(1, (datetime.now() - first_dt).days)
                days_per_unit = total_days / units
                
                days_remaining = int(valid_stock * days_per_unit)
                now = datetime.now()
                expected_dt = now + timedelta(days=days_remaining)
                
                # Confidence Interval Boundary Calculations
                min_runout = now + timedelta(days=int(days_remaining * (1 - error_margin)))
                max_runout = now + timedelta(days=int(days_remaining * (1 + error_margin)))
                
                forecasts.append({
                    **role,
                    "days_remaining": days_remaining,
                    "expected_restock": expected_dt.strftime('%Y-%m-%d'),
                    "min_runout": min_runout.strftime('%Y-%m-%d'),
                    "max_runout": max_runout.strftime('%Y-%m-%d'),
                    "confidence": conf,
                    "stock_on_hand": valid_stock,
                    "history": history_points,
                    "status": "Calculated"
                })
            else:
                # Fallback for roles with no usage data yet
                forecasts.append({
                    **role, 
                    "days_remaining": 9999, 
                    "status": "Insufficient Data", 
                    "confidence": "N/A",
                    "stock_on_hand": valid_stock, 
                    "history": history_points
                })

        forecasts.sort(key=lambda x: x['days_remaining'])
        return {"forecast": forecasts}
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
    cursor = conn.cursor()
    
    # 1. ENFORCE THE RULES: Turn on strict foreign key checking
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # 2. Insert the event into the ledger
        cursor.execute("""
            INSERT INTO INVENTORY_EVENT (product_id, event_type, event_date, cost_sgd, quantity)
            VALUES (?, ?, ?, ?, ?)
        """, (event.product_id, event.event_type, event.event_date, event.cost_sgd, event.quantity))
        
        conn.commit()
        
    except sqlite3.IntegrityError as e:
        # If the product_id doesn't exist, this specific error fires
        raise HTTPException(status_code=400, detail=f"Data integrity error: {str(e)}")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {"message": "Inventory event logged successfully."}

from pydantic import BaseModel
from typing import Optional

class EventUpdate(BaseModel):
    new_event_type: Optional[str] = None
    new_event_date: Optional[str] = None
    quantity: Optional[int] = None
    cost_sgd: Optional[float] = None

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
    conn.row_factory = sqlite3.Row  # Returns dicts instead of tuples
    cursor = conn.cursor()
    
    try:
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
        cursor.execute("""
            INSERT INTO CATEGORY (name)
            VALUES (?)
        """, (category.name,))
        
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
        if category_data.name is None:
            raise HTTPException(status_code=400, detail="Name field is required")
            
        cursor.execute("UPDATE CATEGORY SET name = ? WHERE category_id = ?", 
                       (category_data.name, category_id))
        
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
    cursor.execute("PRAGMA foreign_keys = ON;") # Enforce dependency rules
    
    try:
        cursor.execute("DELETE FROM CATEGORY WHERE category_id = ?", (category_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        conn.commit()
        return {"message": "Category deleted successfully"}
    except sqlite3.IntegrityError:
        # Prevents deleting a category if it's currently linked to a Role
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
        # Join with Category so the UI is readable
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
    
    # ENFORCE THE RULES: Role depends on Category
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        cursor.execute("""
            INSERT INTO ROLE (name, target_buffer_days, category_id)
            VALUES (?, ?, ?)
        """, (role.name, role.target_buffer_days, role.category_id))
        
        conn.commit()
        new_id = cursor.lastrowid
        
    except sqlite3.IntegrityError as e:
        # Blocks you if you pass a fake category_id
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
        # Dynamically build the UPDATE query based on what was provided
        update_fields = []
        params = []
        
        if role_data.name is not None:
            update_fields.append("name = ?")
            params.append(role_data.name)
        if role_data.target_buffer_days is not None:
            update_fields.append("target_buffer_days = ?")
            params.append(role_data.target_buffer_days)
        if role_data.category_id is not None:
            update_fields.append("category_id = ?")
            params.append(role_data.category_id)
            
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