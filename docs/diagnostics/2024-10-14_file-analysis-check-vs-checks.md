# File Analysis: check.py vs checks.py

## ✅ **NO DUPLICATION - These are DIFFERENT files with DIFFERENT purposes**

---

## File Comparison

### **File 1: `backend/app/models/check.py`**

**Purpose:** Database schema definitions (SQLModel/SQLAlchemy ORM)

**Location:** `backend/app/models/check.py`

**What it does:**
- Defines the **database table structure**
- Contains 3 SQLModel classes that map to database tables:
  1. `Check` - Main check table
  2. `Claim` - Claims extracted from checks
  3. `Evidence` - Evidence for each claim

**Key characteristics:**
- Inherits from `SQLModel` (with `table=True`)
- Uses SQLAlchemy Field definitions
- Defines foreign key relationships
- Defines column constraints (ge=0, le=1, default values)
- This is the **source of truth** for database schema

**Lines we modified:**
```python
# Line 49 - Added credibility_score field
credibility_score: float = Field(default=0.6, ge=0, le=1)
```

**Why it exists:**
- Database migrations read this file
- SQLAlchemy uses these classes to create/query tables
- Defines data validation at the database level

---

### **File 2: `backend/app/api/v1/checks.py`**

**Purpose:** API endpoint definitions (FastAPI router)

**Location:** `backend/app/api/v1/checks.py`

**What it does:**
- Defines REST API endpoints (routes) for check operations
- **IMPORTS** the models from `backend/app/models/check.py` (line 9)
- Handles HTTP requests/responses
- Queries database using the imported models
- Transforms database records into JSON responses

**Key line:**
```python
# Line 9 - IMPORTS the models defined in check.py
from app.models import User, Check, Claim, Evidence
```

**Key characteristics:**
- Uses FastAPI router decorators (`@router.post`, `@router.get`)
- Contains endpoint functions (not class definitions)
- Performs CRUD operations on the database
- Serializes database objects to JSON for API responses

**Lines we modified:**
```python
# Line 329 - Added credibility_score to JSON response
"credibilityScore": ev.credibility_score,
```

**Why it exists:**
- Handles API requests from frontend
- Business logic for creating/reading/updating checks
- Authentication/authorization
- Response formatting (database → JSON)

---

## Relationship Diagram

```
┌─────────────────────────────────────────────────────┐
│  Frontend (web/app/dashboard/check/[id]/page.tsx)  │
│                                                     │
│  Calls: GET /api/v1/checks/{id}                    │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP Request
                    ▼
┌─────────────────────────────────────────────────────┐
│  backend/app/api/v1/checks.py                       │
│  (API Endpoint Layer)                               │
│                                                     │
│  @router.get("/{check_id}")                        │
│  async def get_check(...):                          │
│      # Query database using imported models         │
│      stmt = select(Check).where(...)               │
│      check = result.scalar_one_or_none()           │
│                                                     │
│      # Format response (line 329)                   │
│      "credibilityScore": ev.credibility_score      │
└───────────────────┬─────────────────────────────────┘
                    │ Uses (imports)
                    ▼
┌─────────────────────────────────────────────────────┐
│  backend/app/models/check.py                        │
│  (Database Schema Layer)                            │
│                                                     │
│  class Evidence(SQLModel, table=True):              │
│      credibility_score: float = Field(...)  # Line 49 │
│                                                     │
│  This defines the database table structure          │
└─────────────────────────────────────────────────────┘
                    │ Maps to
                    ▼
┌─────────────────────────────────────────────────────┐
│  PostgreSQL Database                                │
│                                                     │
│  evidence table:                                    │
│  ├── id (uuid)                                      │
│  ├── claim_id (uuid FK)                             │
│  ├── source (text)                                  │
│  ├── relevance_score (float)                        │
│  └── credibility_score (float) ← NEW COLUMN        │
└─────────────────────────────────────────────────────┘
```

---

## Why They're Not Duplicates

### **Different Architectural Layers:**

1. **`check.py` = DATA LAYER**
   - Defines "What can be stored in the database"
   - Controls data validation rules
   - Manages relationships between tables

2. **`checks.py` = API LAYER**
   - Defines "How frontend accesses the data"
   - Handles HTTP requests
   - Transforms data between formats (DB ↔ JSON)

### **Analogy:**

Think of it like a library:

- **`check.py`** = The library's catalog system (defines what books exist, how they're organized)
- **`checks.py`** = The librarian's desk (handles checkout requests, searches the catalog, gives you books)

The librarian (checks.py) needs to know about the catalog system (check.py) to do their job, but they serve completely different purposes.

---

## Our Changes Analysis

### **Change 1: `check.py` line 49**
```python
credibility_score: float = Field(default=0.6, ge=0, le=1)
```

**What this does:**
- Creates a new column in the `evidence` database table
- Sets default value to 0.6
- Enforces constraint: must be between 0 and 1
- This is a **schema definition**

### **Change 2: `checks.py` line 329**
```python
"credibilityScore": ev.credibility_score,
```

**What this does:**
- Reads the `credibility_score` value from database
- Includes it in the JSON response to frontend
- Converts snake_case (DB) to camelCase (API)
- This is **response serialization**

---

## Evidence Classes Comparison

### **Only ONE Evidence Class Definition**

There is **only ONE place** where `Evidence` is defined as a class:

```python
# backend/app/models/check.py line 40
class Evidence(SQLModel, table=True):
    # Database table definition
```

All other files **import and use** this class:

```python
# backend/app/api/v1/checks.py line 9
from app.models import Evidence  # Importing, not defining

# backend/app/services/evidence.py
class EvidenceSnippet:  # Different class, used during retrieval
    # Temporary class for pipeline processing, NOT database model
```

---

## Other "Evidence" Classes Found

### **`EvidenceSnippet` in `services/evidence.py`**

This is **NOT a duplicate** - it's a different class for a different purpose:

```python
# backend/app/services/evidence.py line 14
class EvidenceSnippet:
    """Extracted evidence snippet with metadata"""
```

**Purpose:** Temporary data structure used **during** the retrieval pipeline
- Not a database model
- Used to hold extracted text while processing
- Eventually transformed into `Evidence` objects for storage

**Lifecycle:**
1. Pipeline retrieves web content → Creates `EvidenceSnippet`
2. Pipeline calculates scores → Updates `EvidenceSnippet`
3. Pipeline saves to database → Converts to `Evidence` model
4. `EvidenceSnippet` is discarded (temporary)

---

## Verification: No Duplication

### **Check 1: Class Definitions**
```bash
grep -r "class Evidence" backend/
```

**Results:**
- `backend/app/models/check.py`: `class Evidence(SQLModel, table=True):` ✅ Database model
- `backend/app/services/evidence.py`: `class EvidenceSnippet:` ✅ Different class (pipeline helper)

**Conclusion:** No duplicate Evidence classes

### **Check 2: Import Statements**
```bash
grep -r "from.*import.*Evidence" backend/app/api/
```

**Results:**
- `backend/app/api/v1/checks.py` line 9: `from app.models import Evidence`

**Conclusion:** API imports the model (correct pattern)

### **Check 3: Field Definitions**
```bash
grep -r "credibility_score" backend/
```

**Results:**
- `check.py`: **DEFINES** the field (schema)
- `checks.py`: **USES** the field (serialization)
- `retrieve.py`: **CALCULATES** the value (pipeline logic)

**Conclusion:** Each file has a distinct role, no duplication

---

## Standard Backend Pattern

This is the **standard FastAPI/SQLAlchemy pattern**:

```
Models Layer (check.py)
    ↓ defines schema
Database Tables
    ↓ stores data
API Layer (checks.py)
    ↓ queries & formats
JSON Response
    ↓ sends to
Frontend
```

**Every FastAPI project follows this pattern:**
- Models define database structure
- API routes use those models to query data
- Routes serialize model objects to JSON

---

## Conclusion

### ✅ **NO DUPLICATION EXISTS**

1. **Different files, different purposes:**
   - `check.py` = Schema definition
   - `checks.py` = API endpoints

2. **No duplicate classes:**
   - Only ONE `Evidence` class (database model)
   - `EvidenceSnippet` is a different class for pipeline processing

3. **Proper separation of concerns:**
   - Database layer (models)
   - Business logic layer (services)
   - API layer (routes)

4. **Our changes are complementary:**
   - Added field to database model ✅
   - Added field to API response ✅
   - Both changes required, no overlap ✅

### **File Naming Clarity**

The naming is actually **intentional and clear**:

- `check.py` = Singular, because it defines **one set** of related models (Check, Claim, Evidence)
- `checks.py` = Plural, because it handles **multiple operations** on checks (create, list, get, update, delete)

This is a common Python convention:
- Model files are often singular (`user.py`, `product.py`)
- API route files are often plural (`users.py`, `products.py`)

---

## Recommendation

✅ **No changes needed** - The implementation is correct and follows standard FastAPI patterns.

The similarity in names is **expected** and **intentional**:
- `models/check.py` → Data models
- `api/v1/checks.py` → API routes for those models

This is exactly how well-structured backend applications organize their code.
