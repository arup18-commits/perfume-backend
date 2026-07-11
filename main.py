from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
from typing import Optional


# FastAPI Initialization
app = FastAPI(title="ScenTech AI Engine Pro", version="3.0")

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "perfume_db",
    "user": "postgres",
    "password": "123456789",
    "port": "5432"
}

# 🛠️ রিকোয়েস্ট ডাটা মডেল আপডেট (সবগুলোকে Optional করা হয়েছে যাতে ক্র্যাশ না করে)
class FragranceRequest(BaseModel):
    user_id: str
    bottle_size: str
    is_gift: bool = False
    # স্ট্যান্ডার্ড ফিল্ডস
    product_type: Optional[str] = "Perfume"
    occasion: Optional[str] = "Wedding"
    mood: Optional[str] = "Luxury"
    time_of_day: Optional[str] = "Day"
    season: Optional[str] = "Summer"
    longevity: Optional[str] = "8 Hours"
    custom_label: Optional[str] = "Standard"
    # গিফটের নতুন ফিল্ডস
    gift_recipient_gender: Optional[str] = "Unisex"
    gift_recipient_age: Optional[str] = "15-25"
    gift_recipient_vibe: Optional[str] = "Bold"
    gift_packaging: Optional[str] = "Standard Box"
    gift_message: Optional[str] = ""

class OrderRequest(BaseModel):
    user_id: Optional[str] = "scentech_user_id_123"
    formula_id: str
    customer_name: Optional[str] = "Walk-in Customer"
    phone_number: Optional[str] = "01700000000"
    delivery_address: Optional[str] = "Lab Counter"
    custom_label: Optional[str] = "Standard"
    total_price: float

class StatusUpdateRequest(BaseModel):
    order_id: str
    status: str

# Premium Raw Material Pricing Database (USD values)
INGREDIENTS_COST = {
    "Oud": 6.50, "Rose": 4.50, "Jasmine": 4.00, "Musk": 5.00, 
    "Sandalwood": 5.50, "Bergamot": 2.00, "Vanilla": 3.00, 
    "Amber": 3.50, "Lavender": 2.50
}

# ✨ Ingredient Storytelling Database
INGREDIENTS_STORY = {
    "Bergamot": {
        "bangla_name": "বারগামট (সাইট্রাস ফল)",
        "benefit": "এটি মানসিক ক্লান্তি দূর করে তাৎক্ষণিক রিফ্রেশিং ও এনার্জেটিক অনুভূতি দেয়।",
        "story": "ইতালির রৌদ্রোজ্জ্বল উপকূল থেকে সংগৃহীত এই ফলটি পারফিউমে একটি চমৎকার ও উজ্জ্বল প্রথম ইম্প্রেশন তৈরি করে।"
    },
    "Lavender": {
        "bangla_name": "ল্যাভেন্ডার (নীল ফুল)",
        "benefit": "মন শান্ত করে, স্ট্রেস কমায় এবং একটি রাজকীয় মার্জিত ভাব ফুটিয়ে তোলে।",
        "story": "ফ্রেঞ্চ ল্যাভেন্ডার ক্ষেতের স্নিগ্ধতা আপনার চারপাশে একটি প্রশান্তিময় ও অবিজাত পরিবেশ তৈরি করবে।"
    },
    "Rose": {
        "bangla_name": "গোলাপ (পাপড়ি)",
        "benefit": "রোমান্টিক মেজাজ তৈরি করে এবং ব্যক্তিত্বে প্রিমিয়াম আভিজাত্য যোগ করে।",
        "story": "হাজারো তাজা গোলাপের নির্যাস দিয়ে তৈরি এই নোটটি ভালোবাসার এক চিরন্তন ও মোহনীয় গল্প বলে।"
    },
    "Jasmine": {
        "bangla_name": "জেসমিন (চামেলী ফুল)",
        "benefit": "আত্মবিশ্বাস বাড়ায় এবং চারপাশের মানুষকে আকর্ষিত করার তীব্র ক্ষমতা রাখে।",
        "story": "রাতের বেলা ফোটা এই রহস্যময় ফুলের তীব্র মিষ্টি সুঘ্রাণ পারফিউমের প্রধান আকর্ষণ হয়ে দাঁড়ায়।"
    },
    "Oud": {
        "bangla_name": "আগরকাঠ বা ঊদ",
        "benefit": "সবচেয়ে দীর্ঘস্থায়ী ঘ্রাণ নিশ্চিত করে এবং চরম লাক্সারি ও আভিজাত্য প্রকাশ করে।",
        "story": "তরল সোনা নামে পরিচিত এই ঐতিহ্যবাহী মধ্যপ্রাচ্যের উপাদানটি আপনার উপস্থিতিকে রাজকীয় ও গম্ভীর করে তুলবে।"
    },
    "Sandalwood": {
        "bangla_name": "চন্দন কাঠ",
        "benefit": "মনকে স্থির ও গভীর করে এবং সুঘ্রাণে একটি মাটির তৈরি উষ্ণ আভিজাত্য দেয়।",
        "story": "শত বছরের পুরনো চন্দন কাঠের শান্ত ও দীর্ঘস্থায়ী ঘ্রাণ পারফিউমকে একটি ক্লাসিক রূপ দেয়।"
    },
    "Musk": {
        "bangla_name": "কস্তুরী (মাস্ক)",
        "benefit": "ত্বকের সাথে মিশে গিয়ে একটি মখমলের মতো আকর্ষণীয় ও চার্মিং ভাইব তৈরি করে।",
        "story": "হাজার বছর ধরে রাজদরবারে ব্যবহৃত এই উপাদানটি পারফিউমের স্থায়িত্বকে দেয় এক অনন্য উচ্চতা।"
    },
    "Amber": {
        "bangla_name": "অ্যাম্বার (রজন)",
        "benefit": "পারফিউমে একটি মিষ্টি, উষ্ণ এবং আরামদায়ক প্রাচ্যদেশীয় আবহ তৈরি করে।",
        "story": "সোনারঙা অ্যাম্বারের ওম আপনার পারফিউমকে দেয় একটি গ্ল্যামারাস ও আকর্ষণীয় সমাপ্তি।"
    },
    "Vanilla": {
        "bangla_name": "ভ্যানিলা",
        "benefit": "মেজাজ ফুরফুরে করে, নস্টালজিক অনুভূতি জাগায় এবং একটি হালকা মিষ্টি মায়া তৈরি করে।",
        "story": "মাদাগাস্কারের প্রিমিয়াম ভ্যানিলার এই মিষ্টি পরশ আপনার পারফিউমকে করে তুলবে দারুণ আকর্ষণীয়।"
    }
}

# 🧠 AI Fragrance Generation Endpoint
@app.post("/api/v1/generate-fragrance")
async def generate_fragrance(request: FragranceRequest):
    try:
        try:
            size_ml = int(request.bottle_size.lower().replace("ml", ""))
        except:
            size_ml = 50

        # 🎁 গিফট মোড অন থাকলে লজিক ডাইনামিকালি সেট হবে
        if request.is_gift:
            # গিফটের ভাইবকেই আমরা প্রধান 'Mood' হিসেবে ধরব
            current_mood = request.gift_recipient_vibe
            
            # বয়স ও জেন্ডার অনুযায়ী প্রোফাইল সেটআপ
            if current_mood.lower() == "bold":
                recommended_top = ["Bergamot"]
                recommended_heart = ["Jasmine", "Rose"]
                recommended_base = ["Oud", "Musk"]
                top_pct, heart_pct, base_pct = 20, 30, 50
                blend_name = f"Signature Gift - Bold Premium"
                fragrance_profile = f"A charismatic and high-impact formula tailored for a {request.gift_recipient_gender} who loves a bold impression."
                explanation = f"Crafted as a custom gift for the age group {request.gift_recipient_age}. We amplified the Base Notes to 50% using Rich Oud & Musk to match the bold vibe."
            
            elif current_mood.lower() == "elegant":
                recommended_top = ["Lavender", "Bergamot"]
                recommended_heart = ["Rose"]
                recommended_base = ["Sandalwood", "Amber"]
                top_pct, heart_pct, base_pct = 25, 35, 40
                blend_name = f"Signature Gift - Pure Elegance"
                fragrance_profile = f"An exquisite, sophisticated scent trail designed for an elegant persona."
                explanation = f"Perfect choice for an elegant {request.gift_recipient_gender}. Balanced with classic Rose heart notes and warm Sandalwood base notes."
            
            else: # Calm বা অন্য যেকোনো ভাইব
                recommended_top = ["Lavender"]
                recommended_heart = ["Jasmine"]
                recommended_base = ["Vanilla", "Musk"]
                top_pct, heart_pct, base_pct = 30, 40, 30
                blend_name = f"Signature Gift - Serene Calm"
                fragrance_profile = "A soothing, smooth, and peaceful aroma with a cozy comforting vibe."
                explanation = f"Designed specially for a calm mindset. Top notes are focused on calming Lavender to deliver instant serenity."

        else:
            # 🧪 স্ট্যান্ডার্ড মোড (আগের কাস্টমাইজেশন লজিক)
            current_mood = request.mood
            mood_lower = request.mood.lower()
            occasion_lower = request.occasion.lower()
            season_lower = request.season.lower()
            longevity_lower = request.longevity.lower()

            top_pct, heart_pct, base_pct = 25, 35, 40

            if "12+" in longevity_lower or season_lower == "winter" or mood_lower in ["luxury", "woody", "oriental"]:
                top_pct, heart_pct, base_pct = 20, 30, 50
            elif season_lower == "summer" or mood_lower in ["fresh", "citrus"]:
                top_pct, heart_pct, base_pct = 30, 40, 30

            if mood_lower in ["luxury", "oriental", "woody"] or occasion_lower in ["wedding", "party"]:
                recommended_top = ["Bergamot", "Lavender"]
                recommended_heart = ["Rose", "Jasmine"]
                recommended_base = ["Oud", "Sandalwood", "Amber"]
                blend_name = f"Royal {request.mood} Oud"
                fragrance_profile = f"An opulent {request.mood} woody-floral profile crafted for a magnificent presence."
                explanation = f"Because you selected {request.mood} for a {request.occasion}, we pushed the Base Notes to {base_pct}% using Oud and Sandalwood to maximize depth and luxury."
            elif mood_lower in ["fresh", "citrus", "bold"] or occasion_lower in ["office", "casual"]:
                recommended_top = ["Bergamot"]
                recommended_heart = ["Lavender", "Jasmine"]
                recommended_base = ["Musk", "Amber"]
                blend_name = f"Urban {request.mood} Breeze"
                fragrance_profile = "A crisp, energetic, and clean scent profile perfect for daytime freshness."
                explanation = f"For a {request.mood} feeling in {request.season}, we balanced the Top Notes at {top_pct}% with Bergamot to keep it sharp and professional."
            else:
                recommended_top = ["Lavender", "Bergamot"]
                recommended_heart = ["Rose", "Jasmine"]
                recommended_base = ["Vanilla", "Musk"]
                blend_name = f"Midnight {request.mood} Desire"
                fragrance_profile = "A warm, sensual amber-floral trail with a comforting sweet undertone."
                explanation = f"To capture a {request.mood} mood for your {request.occasion}, the formula sets Heart Notes to {heart_pct}% using premium Rose and Jasmine."

        # নোটের রেশিও ক্যালকুলেশন
        top_notes = {ing: round(top_pct / len(recommended_top), 1) for ing in recommended_top}
        heart_notes = {ing: round(heart_pct / len(recommended_heart), 1) for ing in recommended_heart}
        base_notes = {ing: round(base_pct / len(recommended_base), 1) for ing in recommended_base}

        # Compatibility Scoring Engine
        compatibility_score = 95
        if not request.is_gift and (request.season.lower() == "summer" and base_pct >= 45):
            compatibility_score -= 15
        
        compatibility_score = min(max(compatibility_score, 0), 100)
        quality_rating = "Masterpiece Blend 🌟" if compatibility_score >= 90 else "Highly Balanced Blend ✅"

        # 🛠️ Pricing Logic
        essence_ratio = 0.35 if request.product_type == "Attar" else 0.20
        total_essence_ml = size_ml * essence_ratio
        
        raw_material_cost_usd = 0
        for note in [top_notes, heart_notes, base_notes]:
            for ingredient, percentage in note.items():
                ml_used = total_essence_ml * (percentage / 100)
                raw_material_cost_usd += ml_used * INGREDIENTS_COST.get(ingredient, 2.0)

        bottle_cost_usd = 2.50 if size_ml <= 30 else 4.50
        packaging_cost_usd = 3.00
        profit_margin = 0.40
        
        total_cost_usd = raw_material_cost_usd + bottle_cost_usd + packaging_cost_usd
        final_price_usd = total_cost_usd / (1 - profit_margin)

        USD_TO_BDT_RATE = 120.0
        raw_material_cost = round(raw_material_cost_usd * USD_TO_BDT_RATE, 2)
        bottle_cost = round(bottle_cost_usd * USD_TO_BDT_RATE, 2)
        packaging_cost = round(packaging_cost_usd * USD_TO_BDT_RATE, 2)
        final_price = round(final_price_usd * USD_TO_BDT_RATE, 2)

        formula_id = str(uuid.uuid4())
        formula_breakdown = {"top_notes": top_notes, "heart_notes": heart_notes, "base_notes": base_notes}
        
        all_selected_ingredients = list(set(recommended_top + recommended_heart + recommended_base))
        ingredient_stories = {ing: INGREDIENTS_STORY.get(ing, {"bangla_name": ing, "benefit": "প্রিমিয়াম সুঘ্রাণ", "story": "এআই দ্বারা নির্বাচিত উপাদান।"}) for ing in all_selected_ingredients}

        # Save Generated Profile into DB
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'perfume_profiles'")
            prof_cols = [r['column_name'] for r in cur.fetchall()]
            
            if "perfume_name" in prof_cols:
                query = """
                    INSERT INTO perfume_profiles 
                    (id, user_id, perfume_name, product_type, occasion, mood, time_of_day, season, longevity, bottle_size, base_carrier, formula_breakdown, price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(query, (
                    formula_id, request.user_id, blend_name, request.product_type,
                    request.occasion if not request.is_gift else "Gift", current_mood, 
                    request.time_of_day if not request.is_gift else "Universal", 
                    request.season if not request.is_gift else "All-Season",
                    request.longevity if not request.is_gift else "Long Lasting", request.bottle_size, 
                    "Premium Jojoba Oil" if request.product_type == "Attar" else "Ethanol Base",
                    json.dumps(formula_breakdown), final_price
                ))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as db_err:
            print(f"❌ DB Warning: {db_err}")

        return {
            "status": "success",
            "formula_id": formula_id,
            "perfume_name": blend_name,
            "fragrance_profile": fragrance_profile,
            "explanation": explanation,
            "compatibility": {"score": compatibility_score, "rating": quality_rating},
            "formulation": {
                "top_notes": top_notes, "heart_notes": heart_notes, "base_notes": base_notes,
                "top_pct": top_pct, "heart_pct": heart_pct, "base_pct": base_pct
            },
            "pricing": {
                "raw_material_cost": raw_material_cost,
                "bottle_cost": bottle_cost, "packaging_cost": packaging_cost, "final_price": final_price
            },
            "price": final_price,
            "base_carrier": "Premium Jojoba Base" if request.product_type == "Attar" else "Ethanol Alcohol Base (80%)",
            "ingredient_stories": ingredient_stories
        }
    except Exception as e:
        print("❌ General Error in generate-fragrance:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# 🛒 Place Order Endpoint
@app.post("/api/v1/place-order")
async def place_order(order: OrderRequest):
    try:
        order_id = str(uuid.uuid4())
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
        db_columns = [row['column_name'] for row in cur.fetchall()]
        
        insert_fields = ["id", "user_id", "formula_id", "customer_name", "total_price"]
        insert_values = [order_id, order.user_id, order.formula_id, order.customer_name, float(order.total_price)]
        
        if "phone_number" in db_columns:
            insert_fields.append("phone_number")
            insert_values.append(order.phone_number)
        elif "customer_phone" in db_columns:
            insert_fields.append("customer_phone")
            insert_values.append(order.phone_number)
        elif "phone" in db_columns:
            insert_fields.append("phone")
            insert_values.append(order.phone_number)
            
        if "delivery_address" in db_columns:
            insert_fields.append("delivery_address")
            insert_values.append(order.delivery_address)
        elif "customer_address" in db_columns:
            insert_fields.append("customer_address")
            insert_values.append(order.delivery_address)
        elif "address" in db_columns:
            insert_fields.append("address")
            insert_values.append(order.delivery_address)

        if "order_status" in db_columns:
            insert_fields.append("order_status")
            insert_values.append("Pending")

        if "custom_label" in db_columns:
            insert_fields.append("custom_label")
            insert_values.append(order.custom_label)
        elif "bottle_label" in db_columns:
            insert_fields.append("bottle_label")
            insert_values.append(order.custom_label)
        elif "label_text" in db_columns:
            insert_fields.append("label_text")
            insert_values.append(order.custom_label)

        placeholders = ", ".join(["%s"] * len(insert_values))
        columns_str = ", ".join(insert_fields)
        
        query = f"INSERT INTO orders ({columns_str}) VALUES ({placeholders})"
        cur.execute(query, tuple(insert_values))
        conn.commit()
        
        cur.close()
        conn.close()
        return {"status": "success", "message": "Order placed successfully!", "order_id": order_id}
    except Exception as e:
        print("❌ Error in place-order:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# 📋 Get All Orders Endpoint
@app.get("/api/v1/get-orders")
async def get_orders():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
        db_columns = [row['column_name'] for row in cur.fetchall()]
        
        if "order_date" in db_columns:
            cur.execute("SELECT * FROM orders ORDER BY order_date DESC;")
        else:
            cur.execute("SELECT * FROM orders ORDER BY id DESC;")
            
        orders = cur.fetchall()
        cur.close()
        conn.close()
        return {"status": "success", "orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔄 Update Order Status Endpoint
@app.put("/api/v1/update-order-status")
async def update_order_status(request: StatusUpdateRequest):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = "UPDATE orders SET order_status = %s WHERE id = %s"
        cur.execute(query, (request.status, request.order_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": f"Order status updated to {request.status}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📊 Admin Analytics Endpoint
@app.get("/api/v1/admin/analytics")
async def get_admin_analytics():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT COUNT(id) as total_orders, COALESCE(SUM(total_price), 0) as total_revenue FROM orders;")
        sales_summary = cur.fetchone()
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
        db_columns = [row['column_name'] for row in cur.fetchall()]
        
        status_summary = {}
        if "order_status" in db_columns:
            cur.execute("SELECT order_status, COUNT(id) as count FROM orders GROUP BY order_status;")
            status_rows = cur.fetchall()
            status_summary = {row['order_status']: row['count'] for row in status_rows}
        
        cur.execute("""
            SELECT mood, COUNT(id) as count 
            FROM perfume_profiles 
            GROUP BY mood 
            ORDER BY count DESC 
            LIMIT 5;
        """)
        popular_moods = cur.fetchall()
        if not popular_moods:
            popular_moods = []
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "total_orders": sales_summary["total_orders"] if sales_summary else 0,
                "total_revenue": round(sales_summary["total_revenue"], 2) if sales_summary else 0,
                "order_status_breakdown": status_summary,
                "trending_moods": popular_moods
            }
        }
    except Exception as e:
        print("❌ Error in admin analytics:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# 🗑️ Clear All Test Data Endpoint
@app.delete("/api/v1/clear-all-data")
async def clear_all_data():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE orders RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE perfume_profiles RESTART IDENTITY CASCADE;")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"status": "success", "message": "All orders and trending profiles wiped clean successfully!"}
    except Exception as e:
        print("❌ Error in clear-all-data:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 💡 পোর্ট ৮০০১ জ্যাম থাকলে এখান থেকেই সরাসরি ৮MDA বা ৮০০৫ করে দেওয়া যাবে
    uvicorn.run("main:app", host="127.0.0.1", port=8005, reload=True, workers=1)