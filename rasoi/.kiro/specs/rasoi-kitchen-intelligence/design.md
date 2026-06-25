# Design Document: RasOI Kitchen Intelligence

## Overview

RasOI is a multimodal AI-powered kitchen intelligence web application that reduces food waste through intelligent pantry management. The system leverages Claude Sonnet 4 Vision API for image processing and Claude Sonnet 4 Text API for recipe generation and substitutions.

### Key Design Principles

1. **Multimodal Input First**: Prioritize seamless image-to-data pipeline for ingredient scanning
2. **AI-Driven Intelligence**: Leverage Claude Sonnet 4's capabilities for vision and text processing
3. **User Experience Focus**: Provide engaging, contextual guidance through Chammach mascot
4. **Hackathon-Ready**: Optimize for 12-hour build timeline with clear separation of concerns
5. **Data Integrity**: Ensure round-trip consistency for all parsing and serialization operations

### Technology Stack

- **Frontend**: React 18 with TypeScript, Tailwind CSS, React Router
- **Backend**: FastAPI (Python 3.11+), Pydantic for validation
- **AI Services**: Anthropic Claude Sonnet 4 Vision and Text APIs
- **Storage**: SQLite for development/demo (easily upgradeable to PostgreSQL)
- **State Management**: React Context API + useReducer
- **HTTP Client**: Axios (frontend), httpx (backend)

## Architecture

### System Architecture

The application follows a three-tier architecture with clear separation between presentation, business logic, and AI services:

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Scanner │  │  Pantry  │  │   Meal   │  │  Recipe  │   │
│  │   View   │  │   View   │  │   Recs   │  │   View   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│         │              │              │              │       │
│         └──────────────┴──────────────┴──────────────┘       │
│                          │                                    │
│                  ┌───────▼────────┐                          │
│                  │  API Service   │                          │
│                  │  (Axios)       │                          │
│                  └───────┬────────┘                          │
└──────────────────────────┼───────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼───────────────────────────────────┐
│                  Backend (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Router Layer                         │   │
│  │  /scan  /pantry  /recipes  /substitute  /health      │   │
│  └────────────────────┬──────────────────────────────────┘   │
│                       │                                       │
│  ┌────────────────────▼──────────────────────────────────┐  │
│  │           Service Layer                                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │  │
│  │  │  Scanner   │  │   Pantry   │  │   Recipe   │      │  │
│  │  │  Service   │  │  Service   │  │  Service   │      │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘      │  │
│  └────────┼───────────────┼───────────────┼─────────────┘  │
│           │               │               │                  │
│  ┌────────▼───────────────▼───────────────▼─────────────┐  │
│  │            Claude AI Client Layer                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐          │  │
│  │  │   Vision Client  │  │    Text Client   │          │  │
│  │  └──────────────────┘  └──────────────────┘          │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │            Data Access Layer                           │  │
│  │  ┌──────────────────┐  ┌──────────────────┐          │  │
│  │  │  Pantry Repo     │  │   Parser Utils   │          │  │
│  │  └──────────────────┘  └──────────────────┘          │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              External Services                                │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  Claude Vision   │  │   Claude Text    │                 │
│  │   API (4.0)      │  │    API (4.0)     │                 │
│  └──────────────────┘  └──────────────────┘                 │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

#### 1. Ingredient Scanning Flow

```
User uploads image
    ↓
Frontend validates file type/size
    ↓
POST /api/scan with multipart form data
    ↓
Backend Scanner Service receives image
    ↓
Vision Client sends to Claude Vision API
    ↓
Parse Vision API response → Ingredient objects
    ↓
Validate and enrich with estimated expiration
    ↓
Store in Pantry Repository
    ↓
Return parsed ingredients to Frontend
    ↓
Frontend updates Pantry View
```

#### 2. Recipe Recommendation Flow

```
User requests recipes
    ↓
Frontend calls GET /api/recipes
    ↓
Backend Pantry Service fetches all ingredients
    ↓
Recipe Service prioritizes expiring items
    ↓
Text Client sends prompt to Claude Text API
    ↓
Parse recipe response → Recipe objects
    ↓
Return recipes with ingredient matching
    ↓
Frontend displays recipes with Chammach guidance
```

#### 3. Substitution Flow

```
User views recipe with missing ingredients
    ↓
Frontend calls POST /api/substitute
    ↓
Backend receives recipe + missing ingredients
    ↓
Pantry Service fetches available ingredients
    ↓
Text Client sends substitution prompt to Claude
    ↓
Parse substitution response → Substitution objects
    ↓
Return substitution suggestions
    ↓
Frontend displays alternatives in Recipe View
```

## Components and Interfaces

### Frontend Components

#### 1. App Component (Root)

**Responsibility**: Application shell, routing, global state management

**State**:
```typescript
interface AppState {
  pantryItems: PantryItem[];
  isLoading: boolean;
  error: string | null;
}
```

**Routes**:
- `/` - Home/Scanner View
- `/pantry` - Pantry Inventory View
- `/recipes` - Meal Recommendations View
- `/recipe/:id` - Recipe Detail/Step-by-Step View

#### 2. Scanner Component

**Responsibility**: Image upload interface, file validation, scanning feedback

**Props**:
```typescript
interface ScannerProps {
  onScanComplete: (ingredients: Ingredient[]) => void;
  onScanError: (error: string) => void;
}
```

**Key Features**:
- Drag-and-drop or click-to-upload
- Image preview before upload
- Loading spinner during processing
- Support for both ingredient photos and receipt images
- File type validation (JPEG, PNG, max 5MB)

#### 3. PantryView Component

**Responsibility**: Display inventory, manage CRUD operations, highlight expiring items

**Props**:
```typescript
interface PantryViewProps {
  items: PantryItem[];
  onUpdateItem: (id: string, updates: Partial<PantryItem>) => void;
  onDeleteItem: (id: string) => void;
}
```

**Key Features**:
- Sorted list by expiration date
- Visual indicators for expiring/expired items
- Inline editing for quantities
- Delete confirmation modal
- Empty state with call-to-action to scan

#### 4. RecipeList Component

**Responsibility**: Display meal recommendations, show ingredient matching

**Props**:
```typescript
interface RecipeListProps {
  recipes: Recipe[];
  pantryItems: PantryItem[];
  onSelectRecipe: (recipe: Recipe) => void;
}
```

**Key Features**:
- Recipe cards with image, name, prep time
- Ingredient match percentage
- Badge for recipes using expiring items
- Filter by cuisine type (optional)

#### 5. RecipeView Component

**Responsibility**: Step-by-step cooking interface, ingredient substitutions

**Props**:
```typescript
interface RecipeViewProps {
  recipe: Recipe;
  currentStep: number;
  onNextStep: () => void;
  onPrevStep: () => void;
  onRequestSubstitution: (ingredient: string) => void;
}
```

**Key Features**:
- Large, readable step text
- Progress indicator (step X of Y)
- Timer integration for timed steps
- Substitution suggestions inline
- Navigation controls (prev/next)

#### 6. Chammach Component

**Responsibility**: Animated mascot with contextual messages

**Props**:
```typescript
interface ChammachProps {
  message: string;
  context: 'idle' | 'pantry' | 'recipes' | 'cooking';
  animate: boolean;
}
```

**Key Features**:
- CSS/Lottie animations
- Speech bubble with dynamic text
- Context-aware positioning
- Idle animations when inactive

### Backend API Endpoints

#### 1. POST /api/scan

**Purpose**: Upload and process ingredient/receipt images

**Request**:
```typescript
Content-Type: multipart/form-data
{
  image: File,
  scanType: 'ingredient' | 'receipt'
}
```

**Response**:
```typescript
{
  success: boolean,
  ingredients: Ingredient[],
  message?: string
}

interface Ingredient {
  name: string,
  quantity: number,
  unit: string,
  acquisitionDate: string,
  expirationDate: string,
  confidence: number
}
```

**Error Responses**:
- 400: Invalid image format or size
- 422: Vision API parsing failure
- 500: Server error

#### 2. GET /api/pantry

**Purpose**: Retrieve all pantry items

**Response**:
```typescript
{
  items: PantryItem[]
}

interface PantryItem {
  id: string,
  name: string,
  quantity: number,
  unit: string,
  acquisitionDate: string,
  expirationDate: string,
  isExpiring: boolean,
  isExpired: boolean
}
```

#### 3. PUT /api/pantry/{item_id}

**Purpose**: Update pantry item quantity or dates

**Request**:
```typescript
{
  quantity?: number,
  expirationDate?: string
}
```

**Response**:
```typescript
{
  success: boolean,
  item: PantryItem
}
```

#### 4. DELETE /api/pantry/{item_id}

**Purpose**: Remove item from pantry

**Response**:
```typescript
{
  success: boolean,
  message: string
}
```

#### 5. GET /api/recipes

**Purpose**: Get meal recommendations based on pantry

**Query Parameters**:
- `prioritize_expiring`: boolean (default: true)
- `max_recipes`: integer (default: 5)

**Response**:
```typescript
{
  recipes: Recipe[]
}

interface Recipe {
  id: string,
  name: string,
  ingredients: RecipeIngredient[],
  steps: string[],
  prepTimeMinutes: number,
  matchPercentage: number,
  usesExpiringItems: boolean,
  missingIngredients: string[]
}

interface RecipeIngredient {
  name: string,
  quantity: number,
  unit: string,
  available: boolean
}
```

#### 6. POST /api/substitute

**Purpose**: Get ingredient substitution suggestions

**Request**:
```typescript
{
  recipeId: string,
  missingIngredient: string,
  recipeContext: string
}
```

**Response**:
```typescript
{
  substitutions: Substitution[]
}

interface Substitution {
  ingredient: string,
  ratio: string,
  notes: string,
  available: boolean
}
```

#### 7. GET /api/health

**Purpose**: Health check endpoint

**Response**:
```typescript
{
  status: 'healthy',
  timestamp: string,
  services: {
    database: 'up' | 'down',
    claudeVision: 'up' | 'down',
    claudeText: 'up' | 'down'
  }
}
```

### Backend Service Layer

#### 1. ScannerService

**Responsibility**: Coordinate image processing and ingredient extraction

**Methods**:
```python
class ScannerService:
    async def scan_image(
        self, 
        image_bytes: bytes, 
        scan_type: ScanType
    ) -> List[Ingredient]:
        """
        Process image and extract ingredients.
        
        Flow:
        1. Validate image format and size
        2. Send to Vision Client
        3. Parse response using IngredientParser
        4. Enrich with expiration estimates
        5. Store in PantryRepository
        6. Return ingredient list
        """
        pass
    
    def estimate_expiration(
        self, 
        ingredient_name: str, 
        acquisition_date: date
    ) -> date:
        """
        Estimate expiration based on ingredient category.
        Uses hardcoded lookup for hackathon demo.
        """
        pass
```

#### 2. PantryService

**Responsibility**: Manage pantry inventory operations

**Methods**:
```python
class PantryService:
    async def get_all_items(self) -> List[PantryItem]:
        """Fetch all items with expiration status computed."""
        pass
    
    async def add_item(self, ingredient: Ingredient) -> PantryItem:
        """Add new item to pantry."""
        pass
    
    async def update_item(
        self, 
        item_id: str, 
        updates: PantryItemUpdate
    ) -> PantryItem:
        """Update existing item."""
        pass
    
    async def delete_item(self, item_id: str) -> bool:
        """Remove item from pantry."""
        pass
    
    def get_expiring_items(
        self, 
        days: int = 3
    ) -> List[PantryItem]:
        """Get items expiring within N days."""
        pass
```

#### 3. RecipeService

**Responsibility**: Generate meal recommendations

**Methods**:
```python
class RecipeService:
    async def get_recommendations(
        self,
        pantry_items: List[PantryItem],
        prioritize_expiring: bool = True,
        max_recipes: int = 5
    ) -> List[Recipe]:
        """
        Generate recipe recommendations.
        
        Flow:
        1. Fetch pantry items
        2. Build prompt with expiring items priority
        3. Send to Text Client
        4. Parse response using RecipeParser
        5. Calculate match percentages
        6. Return sorted recipes
        """
        pass
    
    def calculate_match_percentage(
        self,
        recipe: Recipe,
        pantry_items: List[PantryItem]
    ) -> float:
        """Calculate % of recipe ingredients available in pantry."""
        pass
```

#### 4. SubstitutionService

**Responsibility**: Generate ingredient substitutions

**Methods**:
```python
class SubstitutionService:
    async def get_substitutions(
        self,
        missing_ingredient: str,
        recipe_context: str,
        available_ingredients: List[str]
    ) -> List[Substitution]:
        """
        Get substitution suggestions.
        
        Flow:
        1. Build prompt with recipe context
        2. Include available pantry ingredients
        3. Send to Text Client
        4. Parse response using SubstitutionParser
        5. Return substitution list
        """
        pass
```

### AI Client Layer

#### 1. ClaudeVisionClient

**Responsibility**: Interface with Claude Sonnet 4 Vision API

**Methods**:
```python
class ClaudeVisionClient:
    def __init__(self, api_key: str, max_retries: int = 2):
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str
    ) -> VisionResponse:
        """
        Send image to Claude Vision API with retry logic.
        
        Returns parsed JSON response from Claude.
        Raises VisionAPIError on failure after retries.
        """
        pass
    
    def build_ingredient_prompt(self, scan_type: ScanType) -> str:
        """Build structured prompt for ingredient extraction."""
        pass
    
    def build_receipt_prompt(self) -> str:
        """Build structured prompt for receipt parsing."""
        pass
```

**Prompts**:
- Ingredient Photo: "Analyze this image and extract all visible ingredients. For each ingredient, provide: name, estimated quantity, unit of measurement, and recommended storage duration in days. Return as JSON array."
- Receipt: "Extract all food items from this grocery receipt. For each item, provide: name, quantity if visible, unit, and purchase date. Return as JSON array."

#### 2. ClaudeTextClient

**Responsibility**: Interface with Claude Sonnet 4 Text API

**Methods**:
```python
class ClaudeTextClient:
    def __init__(self, api_key: str, max_retries: int = 2):
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def generate_recipes(
        self,
        ingredients: List[str],
        expiring_items: List[str],
        max_recipes: int
    ) -> TextResponse:
        """
        Generate recipe recommendations.
        
        Returns structured JSON with recipes.
        Raises TextAPIError on failure after retries.
        """
        pass
    
    async def generate_substitutions(
        self,
        missing_ingredient: str,
        recipe_context: str,
        available_ingredients: List[str]
    ) -> TextResponse:
        """Generate substitution suggestions."""
        pass
```

**Prompts**:
- Recipe Generation: "Given these available ingredients: {ingredients}, prioritizing these expiring items: {expiring}, generate {max_recipes} recipes. For each recipe, provide: name, full ingredient list with quantities, step-by-step instructions, and estimated prep time. Return as JSON array."
- Substitution: "In the recipe '{recipe_context}', suggest substitutions for '{missing_ingredient}' using these available ingredients: {available}. Provide substitution ratio and preparation notes. Return as JSON array."

### Data Access Layer

#### 1. PantryRepository

**Responsibility**: Persist and retrieve pantry data

**Methods**:
```python
class PantryRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def create(self, item: PantryItem) -> PantryItem:
        """Insert new pantry item."""
        pass
    
    async def get_all(self) -> List[PantryItem]:
        """Retrieve all pantry items."""
        pass
    
    async def get_by_id(self, item_id: str) -> Optional[PantryItem]:
        """Get single item by ID."""
        pass
    
    async def update(
        self, 
        item_id: str, 
        updates: Dict[str, Any]
    ) -> PantryItem:
        """Update item fields."""
        pass
    
    async def delete(self, item_id: str) -> bool:
        """Delete item by ID."""
        pass
```

**Schema**:
```sql
CREATE TABLE pantry_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    acquisition_date TEXT NOT NULL,
    expiration_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_expiration_date ON pantry_items(expiration_date);
```

#### 2. Parser Utilities

**Responsibility**: Parse and serialize AI API responses

**Classes**:

```python
class IngredientParser:
    """Parse Vision API responses into Ingredient objects."""
    
    @staticmethod
    def parse(response: str) -> List[Ingredient]:
        """Parse JSON string to Ingredient list."""
        pass
    
    @staticmethod
    def pretty_print(ingredients: List[Ingredient]) -> str:
        """Serialize Ingredient list to JSON string."""
        pass

class RecipeParser:
    """Parse Text API recipe responses into Recipe objects."""
    
    @staticmethod
    def parse(response: str) -> List[Recipe]:
        """Parse JSON string to Recipe list."""
        pass
    
    @staticmethod
    def pretty_print(recipes: List[Recipe]) -> str:
        """Serialize Recipe list to JSON string."""
        pass

class SubstitutionParser:
    """Parse Text API substitution responses."""
    
    @staticmethod
    def parse(response: str) -> List[Substitution]:
        """Parse JSON string to Substitution list."""
        pass
    
    @staticmethod
    def pretty_print(subs: List[Substitution]) -> str:
        """Serialize Substitution list to JSON string."""
        pass
```

## Data Models

### Frontend TypeScript Models

```typescript
// Pantry Item
interface PantryItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  acquisitionDate: string; // ISO 8601
  expirationDate: string;  // ISO 8601
  isExpiring: boolean;
  isExpired: boolean;
}

// Ingredient (from scan)
interface Ingredient {
  name: string;
  quantity: number;
  unit: string;
  acquisitionDate: string;
  expirationDate: string;
  confidence: number; // 0-1 from Vision API
}

// Recipe
interface Recipe {
  id: string;
  name: string;
  ingredients: RecipeIngredient[];
  steps: string[];
  prepTimeMinutes: number;
  matchPercentage: number;
  usesExpiringItems: boolean;
  missingIngredients: string[];
}

interface RecipeIngredient {
  name: string;
  quantity: number;
  unit: string;
  available: boolean;
}

// Substitution
interface Substitution {
  ingredient: string;
  ratio: string;
  notes: string;
  available: boolean;
}

// Chammach Message
interface ChammachMessage {
  text: string;
  context: 'idle' | 'pantry' | 'recipes' | 'cooking';
  duration: number; // milliseconds
}
```

### Backend Python Models (Pydantic)

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import List, Optional
from enum import Enum

class ScanType(str, Enum):
    INGREDIENT = "ingredient"
    RECEIPT = "receipt"

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str
    acquisition_date: date
    expiration_date: date
    confidence: float = Field(ge=0.0, le=1.0)

class PantryItem(BaseModel):
    id: str
    name: str
    quantity: float
    unit: str
    acquisition_date: date
    expiration_date: date
    created_at: datetime
    updated_at: datetime
    
    @property
    def is_expiring(self) -> bool:
        """Returns True if expiring within 3 days."""
        days_until_expiry = (self.expiration_date - date.today()).days
        return 0 <= days_until_expiry <= 3
    
    @property
    def is_expired(self) -> bool:
        """Returns True if expiration date has passed."""
        return self.expiration_date < date.today()

class PantryItemUpdate(BaseModel):
    quantity: Optional[float] = None
    expiration_date: Optional[date] = None

class RecipeIngredient(BaseModel):
    name: str
    quantity: float
    unit: str
    available: bool

class Recipe(BaseModel):
    id: str
    name: str
    ingredients: List[RecipeIngredient]
    steps: List[str]
    prep_time_minutes: int
    match_percentage: float = Field(ge=0.0, le=100.0)
    uses_expiring_items: bool
    missing_ingredients: List[str]

class Substitution(BaseModel):
    ingredient: str
    ratio: str
    notes: str
    available: bool

class VisionResponse(BaseModel):
    """Raw response from Claude Vision API."""
    content: str
    model: str
    usage: dict

class TextResponse(BaseModel):
    """Raw response from Claude Text API."""
    content: str
    model: str
    usage: dict
```

### Database Schema

```sql
-- Pantry Items Table
CREATE TABLE pantry_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    quantity REAL NOT NULL CHECK(quantity >= 0),
    unit TEXT NOT NULL,
    acquisition_date TEXT NOT NULL,
    expiration_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expiration_date ON pantry_items(expiration_date);
CREATE INDEX idx_name ON pantry_items(name);

-- Trigger to update updated_at on modification
CREATE TRIGGER update_pantry_items_updated_at
AFTER UPDATE ON pantry_items
FOR EACH ROW
BEGIN
    UPDATE pantry_items SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

**Property Reflection:**

After analyzing all acceptance criteria, I've identified the following properties that test OUR code logic (not external service behavior). Several criteria test Claude API behavior or infrastructure wiring and are better suited for integration tests.

**Properties Eliminated as Redundant:**
- **2.7 (Pantry count invariant)** is subsumed by **2.2 (add ingredient)** and **2.4 (delete ingredient)** - if add and delete work correctly, count invariant follows
- **3.4 (Sort expiring items)** is redundant with **2.6 (Sort all items by expiration)** - same sorting logic
- **4.1 and 4.4** both test expiring item prioritization - combined into single property
- **10.4 (Parse Vision responses)** is covered by **12.2 (Vision parser field extraction)** - same parsing logic
- **10.5 (Parse Text responses)** is covered by **13.2 (Recipe parser field extraction)** - same parsing logic

**Properties Combined:**
- **7.2, 7.3, 7.4** (Chammach contextual guidance) combined into single property about context-aware messaging

### Property 1: Vision Parser Round-Trip

*For any* valid Vision AI JSON response containing ingredient data, parsing the response then pretty-printing it back to JSON then parsing again SHALL produce equivalent ingredient objects.

**Validates: Requirements 1.6, 12.4**

### Property 2: Recipe Parser Round-Trip

*For any* valid Text AI recipe response, parsing the response then pretty-printing it back to JSON then parsing again SHALL produce equivalent recipe objects.

**Validates: Requirements 13.4**

### Property 3: Storage Round-Trip

*For any* valid pantry item, writing it to persistent storage then reading it back SHALL produce an equivalent pantry item with all fields preserved.

**Validates: Requirements 11.5**

### Property 4: Ingredient Addition Persistence

*For any* valid ingredient with name, quantity, unit, and expiration date, adding it to the pantry SHALL result in the ingredient being stored and retrievable by its ID.

**Validates: Requirements 2.2**

### Property 5: Ingredient Deletion Completeness

*For any* pantry item that exists in storage, deleting it by ID SHALL result in the item no longer being retrievable and not appearing in the full pantry list.

**Validates: Requirements 2.4**

### Property 6: Quantity Update Persistence

*For any* existing pantry item and any positive quantity value, updating the item's quantity SHALL result in the stored quantity being modified and the new value being retrievable.

**Validates: Requirements 2.5**

### Property 7: Expiration Date Sorting

*For any* list of pantry items with varying expiration dates, sorting the list SHALL order items with earliest expiration dates first, maintaining stable sort for items with identical dates.

**Validates: Requirements 2.6, 3.4**

### Property 8: Expiring Item Detection

*For any* pantry item with an expiration date, if the date is within 3 days of the current system date (inclusive), the item SHALL be flagged as expiring; if the date is in the past, the item SHALL be flagged as expired.

**Validates: Requirements 3.1, 3.5**

### Property 9: Pantry Display Completeness

*For any* pantry inventory state with N items stored, displaying the pantry SHALL render all N items with their name, quantity, unit, and expiration date visible.

**Validates: Requirements 2.3**

### Property 10: Expiring Item Visual Highlighting

*For any* pantry view containing items flagged as expiring or expired, those items SHALL have distinct CSS classes or visual indicators applied that differ from non-expiring items.

**Validates: Requirements 3.2, 3.5**

### Property 11: Vision Response Field Validation

*For any* Vision AI response JSON, validation SHALL accept responses containing required fields (ingredient name, acquisition date) and SHALL reject responses missing either required field, regardless of other fields present.

**Validates: Requirements 1.4**

### Property 12: Vision Parser Field Extraction

*For any* valid Vision AI response containing ingredient data, the parser SHALL successfully extract ingredient name, quantity, unit, and date fields into structured Ingredient objects.

**Validates: Requirements 12.2**

### Property 13: Recipe Field Extraction

*For any* valid Text AI recipe response, the parser SHALL extract recipe name, ingredients list (with quantities and units), steps array, and preparation time into structured Recipe objects.

**Validates: Requirements 4.5, 13.2**

### Property 14: Recipe Ingredient Matching

*For any* recipe with N ingredients and any pantry inventory, calculating match percentage SHALL return (count of available ingredients / N) × 100, and missing ingredients SHALL be the set of recipe ingredients not present in the pantry by name.

**Validates: Requirements 4.6**

### Property 15: Substitution Ratio Extraction

*For any* Text AI substitution response containing substitution suggestions, the parser SHALL extract ingredient name, substitution ratio string, and notes for each suggestion.

**Validates: Requirements 5.3**

### Property 16: Recipe Step Navigation State

*For any* recipe with M steps and any current step position P (where 1 ≤ P ≤ M), navigating away from the recipe view and returning to it SHALL restore the step position to P.

**Validates: Requirements 6.4**

### Property 17: Recipe Step Display Completeness

*For any* recipe step being viewed, the display SHALL render the step instructions text, required ingredients for that step, and timing information if specified.

**Validates: Requirements 6.3**

### Property 18: Chammach Contextual Messaging

*For any* application context (pantry view with expiring items, recipe recommendations, or active cooking step), Chammach SHALL display messages relevant to that context, mentioning expiring items in pantry view, explaining recipe selection in recommendations, and providing step-specific tips during cooking.

**Validates: Requirements 7.2, 7.3, 7.4**

### Property 19: Request Payload Validation

*For any* API endpoint request with required fields specified in the endpoint schema, validation SHALL accept requests containing all required fields with correct types and SHALL reject requests missing required fields or containing incorrect types, returning validation error details.

**Validates: Requirements 9.5**

### Property 20: Expiring Item Prioritization in Recommendations

*For any* pantry inventory containing both expiring and non-expiring items, recipe recommendations SHALL prioritize recipes that use expiring items, such that recipes using expiring ingredients appear before recipes using only non-expiring ingredients.

**Validates: Requirements 4.1, 4.4**

### Property 21: Upload Loading Indicator Display

*For any* image upload operation initiated by the user, the frontend SHALL display a loading indicator immediately upon upload start and SHALL hide the indicator only after receiving a response (success or error) from the backend.

**Validates: Requirements 8.3**

### Property 22: Error Message Display

*For any* failed operation (API error, validation failure, or network error), the frontend SHALL display an error message to the user containing description of what failed.

**Validates: Requirements 8.5**

### Property 23: Pantry Item Retrieval Completeness

*For any* set of pantry items stored in persistent storage, loading the pantry inventory SHALL retrieve all stored items without omission or duplication.

**Validates: Requirements 11.3**


## Error Handling

### Error Categories

The application handles four categories of errors:

1. **Client Errors (4xx)**: Invalid user input, validation failures
2. **Server Errors (5xx)**: Internal service failures, unhandled exceptions
3. **External Service Errors**: Claude API failures, rate limiting, network issues
4. **Data Errors**: Parsing failures, malformed responses, data integrity issues

### Frontend Error Handling

#### Error Display Strategy

```typescript
interface ErrorState {
  type: 'validation' | 'network' | 'server' | 'parsing';
  message: string;
  details?: string;
  recoverable: boolean;
}
```

**Error UI Components:**
- **Toast Notifications**: Temporary errors (network glitches, retryable failures)
- **Error Banners**: Persistent errors requiring user action (invalid input, missing data)
- **Modal Dialogs**: Critical errors requiring acknowledgment (service unavailable)
- **Inline Validation**: Field-level errors in forms (file type, size validation)

**User-Friendly Error Messages:**
- **Upload Failure**: "We couldn't process that image. Please try a clearer photo with better lighting."
- **Network Error**: "Connection lost. Check your internet and try again."
- **API Rate Limit**: "Too many requests. Please wait a moment and try again."
- **Parsing Error**: "We couldn't understand the image. Try uploading a different photo."
- **Empty Pantry**: "Your pantry is empty! Upload ingredient photos to get started."

#### Error Recovery Actions

- **Retry Button**: For transient network/API failures
- **Upload Alternative**: Suggest different image on parsing failure
- **Clear and Retry**: Reset form state for validation errors
- **Contact Support**: For unrecoverable errors (provide error ID)

### Backend Error Handling

#### Exception Hierarchy

```python
class RasOIException(Exception):
    """Base exception for all RasOI errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(RasOIException):
    """Raised when request validation fails."""
    pass

class ParseError(RasOIException):
    """Raised when AI response parsing fails."""
    pass

class ClaudeAPIError(RasOIException):
    """Raised when Claude API requests fail."""
    def __init__(self, message: str, status_code: int, retry_after: int = None):
        super().__init__(message, {"status_code": status_code})
        self.status_code = status_code
        self.retry_after = retry_after

class StorageError(RasOIException):
    """Raised when database operations fail."""
    pass
```

#### Global Exception Handler

```python
@app.exception_handler(RasOIException)
async def rasoi_exception_handler(request: Request, exc: RasOIException):
    """Handle all RasOI exceptions with appropriate responses."""
    status_code = {
        ValidationError: 400,
        ParseError: 422,
        ClaudeAPIError: 502,
        StorageError: 500,
    }.get(type(exc), 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

#### Error Logging

```python
import logging
import structlog

logger = structlog.get_logger()

# Log all errors with context
logger.error(
    "vision_api_failure",
    error_type=type(exc).__name__,
    status_code=exc.status_code if hasattr(exc, 'status_code') else None,
    user_id=request.state.user_id if hasattr(request.state, 'user_id') else None,
    request_id=request.state.request_id,
    details=exc.details
)
```

### Claude API Error Handling

#### Retry Logic with Exponential Backoff

```python
class ClaudeClientWithRetry:
    def __init__(self, max_retries: int = 2, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def call_with_retry(self, api_call: Callable) -> Any:
        """Execute API call with exponential backoff retry."""
        for attempt in range(self.max_retries + 1):
            try:
                return await api_call()
            except anthropic.RateLimitError as e:
                if attempt == self.max_retries:
                    raise ClaudeAPIError(
                        "Rate limit exceeded after retries",
                        status_code=429,
                        retry_after=e.retry_after
                    )
                delay = self.base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            except anthropic.APIError as e:
                if attempt == self.max_retries:
                    raise ClaudeAPIError(
                        f"Claude API error: {str(e)}",
                        status_code=e.status_code
                    )
                await asyncio.sleep(self.base_delay * (2 ** attempt))
            except Exception as e:
                logger.error("unexpected_claude_error", error=str(e))
                raise ClaudeAPIError(
                    "Unexpected error calling Claude API",
                    status_code=500
                )
```

#### Rate Limit Handling

- **Detection**: Catch `anthropic.RateLimitError` exceptions
- **Response**: Return 429 status with `Retry-After` header
- **Frontend**: Display wait message and auto-retry after specified time
- **Monitoring**: Log rate limit events for capacity planning

### Data Validation Errors

#### Request Validation

```python
from pydantic import BaseModel, validator, ValidationError

class ScanRequest(BaseModel):
    scan_type: ScanType
    
    @validator('scan_type')
    def validate_scan_type(cls, v):
        if v not in ['ingredient', 'receipt']:
            raise ValueError('scan_type must be "ingredient" or "receipt"')
        return v

# FastAPI automatically handles ValidationError and returns 422
@app.post("/api/scan")
async def scan_image(
    image: UploadFile = File(...),
    scan_type: ScanType = Form(...)
):
    # Validation happens automatically
    pass
```

#### Image Validation

```python
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/jpg']

async def validate_image(file: UploadFile) -> bytes:
    """Validate image file and return bytes."""
    if file.content_type not in ALLOWED_TYPES:
        raise ValidationError(
            f"Invalid file type: {file.content_type}",
            details={"allowed_types": ALLOWED_TYPES}
        )
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValidationError(
            f"File size {len(content)} exceeds maximum {MAX_FILE_SIZE}",
            details={"max_size_mb": MAX_FILE_SIZE / (1024 * 1024)}
        )
    
    return content
```

### Parsing Error Handling

#### Vision Response Parsing

```python
class IngredientParser:
    @staticmethod
    def parse(response: str) -> List[Ingredient]:
        """Parse Vision AI response with error handling."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ParseError(
                "Invalid JSON in Vision API response",
                details={"error": str(e), "response_preview": response[:100]}
            )
        
        if not isinstance(data, list):
            raise ParseError(
                "Expected array of ingredients in Vision API response",
                details={"type": type(data).__name__}
            )
        
        ingredients = []
        for idx, item in enumerate(data):
            try:
                # Validate required fields
                if 'name' not in item:
                    raise ParseError(
                        f"Missing 'name' field in ingredient {idx}",
                        details={"item": item}
                    )
                
                ingredients.append(Ingredient(
                    name=item['name'],
                    quantity=item.get('quantity', 1.0),
                    unit=item.get('unit', 'unit'),
                    acquisition_date=item.get('acquisition_date', date.today()),
                    expiration_date=item.get('expiration_date', date.today() + timedelta(days=7)),
                    confidence=item.get('confidence', 0.8)
                ))
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(
                    "ingredient_parse_warning",
                    index=idx,
                    error=str(e),
                    item=item
                )
                # Skip malformed items, continue parsing others
                continue
        
        if not ingredients:
            raise ParseError(
                "No valid ingredients extracted from response",
                details={"response": response[:200]}
            )
        
        return ingredients
```

#### Recipe Response Parsing

```python
class RecipeParser:
    @staticmethod
    def parse(response: str) -> List[Recipe]:
        """Parse Text AI recipe response with error handling."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ParseError(
                "Invalid JSON in recipe response",
                details={"error": str(e)}
            )
        
        recipes = []
        for recipe_data in data:
            # Validate required fields
            required_fields = ['name', 'ingredients', 'steps', 'prep_time_minutes']
            missing = [f for f in required_fields if f not in recipe_data]
            if missing:
                raise ParseError(
                    f"Missing required recipe fields: {missing}",
                    details={"recipe": recipe_data.get('name', 'unknown')}
                )
            
            try:
                recipes.append(Recipe(**recipe_data))
            except ValidationError as e:
                logger.error("recipe_validation_error", error=str(e))
                raise ParseError(
                    "Recipe data validation failed",
                    details={"errors": e.errors()}
                )
        
        return recipes
```

### Database Error Handling

#### Connection Errors

```python
class PantryRepository:
    async def _execute_query(self, query: str, params: tuple = ()) -> Any:
        """Execute query with connection error handling."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                await db.commit()
                return cursor
        except aiosqlite.OperationalError as e:
            raise StorageError(
                "Database operation failed",
                details={"error": str(e), "query": query}
            )
        except Exception as e:
            logger.error("unexpected_db_error", error=str(e))
            raise StorageError(
                "Unexpected database error",
                details={"error": str(e)}
            )
```

#### Transaction Rollback

```python
async def update_item(self, item_id: str, updates: Dict[str, Any]) -> PantryItem:
    """Update item with transaction rollback on error."""
    async with aiosqlite.connect(self.db_path) as db:
        try:
            # Begin transaction
            await db.execute("BEGIN TRANSACTION")
            
            # Perform update
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            query = f"UPDATE pantry_items SET {set_clause} WHERE id = ?"
            await db.execute(query, (*updates.values(), item_id))
            
            # Commit transaction
            await db.commit()
            
            # Fetch updated item
            return await self.get_by_id(item_id)
        
        except Exception as e:
            # Rollback on any error
            await db.rollback()
            raise StorageError(
                f"Failed to update item {item_id}",
                details={"error": str(e)}
            )
```

### Graceful Degradation

When non-critical services fail, provide degraded functionality:

- **Chammach Unavailable**: Hide mascot, show plain UI without guidance
- **Substitution Service Down**: Display missing ingredients without substitution suggestions
- **Recipe Images Missing**: Show text-only recipe cards
- **Expiration Estimates Unavailable**: Use default 7-day expiration for all items

## Testing Strategy

### Testing Philosophy

RasOI uses a **dual testing approach** combining unit tests for specific examples and property-based tests for universal behaviors. This ensures both concrete correctness and comprehensive input coverage.

### Property-Based Testing

#### Framework Selection

**Backend (Python)**: [Hypothesis](https://hypothesis.readthedocs.io/) - industry-standard property-based testing for Python

**Frontend (TypeScript)**: [fast-check](https://fast-check.dev/) - most mature PBT library for TypeScript/JavaScript

#### Configuration

All property-based tests MUST run **minimum 100 iterations** to ensure comprehensive input coverage due to randomization.

Each property test MUST include a **tag comment** referencing the design property:

```python
# Feature: rasoi-kitchen-intelligence, Property 1: Vision Parser Round-Trip
@given(vision_responses())
def test_vision_parser_round_trip(vision_response):
    """Test that parsing then printing then parsing Vision AI responses preserves data."""
    # Parse the response
    ingredients = IngredientParser.parse(vision_response)
    
    # Pretty print back to JSON
    json_output = IngredientParser.pretty_print(ingredients)
    
    # Parse again
    ingredients_reparsed = IngredientParser.parse(json_output)
    
    # Assert equivalence
    assert ingredients == ingredients_reparsed
```

### Test Coverage by Layer

#### 1. Parser Tests (Property-Based)

**Focus**: Round-trip properties, field extraction, error handling

**Properties to Test**:
- Property 1: Vision Parser Round-Trip
- Property 2: Recipe Parser Round-Trip
- Property 12: Vision Parser Field Extraction
- Property 13: Recipe Field Extraction
- Property 15: Substitution Ratio Extraction

**Generators**:
```python
from hypothesis import given, strategies as st

@st.composite
def vision_responses(draw):
    """Generate random Vision AI responses."""
    num_ingredients = draw(st.integers(min_value=1, max_value=10))
    ingredients = []
    for _ in range(num_ingredients):
        ingredients.append({
            "name": draw(st.text(min_size=3, max_size=50, alphabet=st.characters(blacklist_categories=['Cs']))),
            "quantity": draw(st.floats(min_value=0.1, max_value=100)),
            "unit": draw(st.sampled_from(['g', 'kg', 'ml', 'l', 'cup', 'tbsp', 'unit'])),
            "acquisition_date": draw(st.dates()).isoformat(),
            "expiration_date": draw(st.dates()).isoformat(),
            "confidence": draw(st.floats(min_value=0.0, max_value=1.0))
        })
    return json.dumps(ingredients)

@st.composite
def recipe_responses(draw):
    """Generate random recipe responses."""
    num_recipes = draw(st.integers(min_value=1, max_value=5))
    recipes = []
    for _ in range(num_recipes):
        num_ingredients = draw(st.integers(min_value=2, max_value=15))
        num_steps = draw(st.integers(min_value=3, max_value=20))
        
        recipes.append({
            "name": draw(st.text(min_size=5, max_size=100)),
            "ingredients": [
                {
                    "name": draw(st.text(min_size=3, max_size=50)),
                    "quantity": draw(st.floats(min_value=0.1, max_value=10)),
                    "unit": draw(st.sampled_from(['g', 'cup', 'tbsp', 'unit'])),
                    "available": draw(st.booleans())
                }
                for _ in range(num_ingredients)
            ],
            "steps": [draw(st.text(min_size=10, max_size=200)) for _ in range(num_steps)],
            "prep_time_minutes": draw(st.integers(min_value=5, max_value=180)),
            "match_percentage": draw(st.floats(min_value=0.0, max_value=100.0)),
            "uses_expiring_items": draw(st.booleans()),
            "missing_ingredients": []
        })
    return json.dumps(recipes)
```

#### 2. Repository Tests (Property-Based + Unit)

**Focus**: CRUD operations, data persistence, round-trip

**Properties to Test**:
- Property 3: Storage Round-Trip
- Property 4: Ingredient Addition Persistence
- Property 5: Ingredient Deletion Completeness
- Property 6: Quantity Update Persistence
- Property 23: Pantry Item Retrieval Completeness

**Example**:
```python
# Feature: rasoi-kitchen-intelligence, Property 3: Storage Round-Trip
@given(pantry_items())
@pytest.mark.asyncio
async def test_storage_round_trip(pantry_item):
    """Test that storing and retrieving pantry items preserves data."""
    repo = PantryRepository(":memory:")
    
    # Write item
    stored_item = await repo.create(pantry_item)
    
    # Read back
    retrieved_item = await repo.get_by_id(stored_item.id)
    
    # Assert equivalence (excluding timestamps)
    assert retrieved_item.name == pantry_item.name
    assert retrieved_item.quantity == pantry_item.quantity
    assert retrieved_item.expiration_date == pantry_item.expiration_date
```

**Unit Tests**:
- Test database schema creation
- Test index creation and performance
- Test concurrent modification handling

#### 3. Service Layer Tests (Property-Based + Unit)

**Focus**: Business logic, expiration detection, sorting, prioritization

**Properties to Test**:
- Property 7: Expiration Date Sorting
- Property 8: Expiring Item Detection
- Property 14: Recipe Ingredient Matching
- Property 20: Expiring Item Prioritization in Recommendations

**Example**:
```python
# Feature: rasoi-kitchen-intelligence, Property 8: Expiring Item Detection
@given(
    expiration_date=st.dates(),
    current_date=st.dates()
)
def test_expiring_item_detection(expiration_date, current_date):
    """Test that expiration detection correctly flags items."""
    days_until_expiry = (expiration_date - current_date).days
    
    item = PantryItem(
        id="test-id",
        name="Test Item",
        quantity=1.0,
        unit="unit",
        acquisition_date=current_date - timedelta(days=1),
        expiration_date=expiration_date,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Set global "today" for testing
    with mock.patch('datetime.date.today', return_value=current_date):
        if 0 <= days_until_expiry <= 3:
            assert item.is_expiring == True
            assert item.is_expired == False
        elif days_until_expiry < 0:
            assert item.is_expired == True
        else:
            assert item.is_expiring == False
            assert item.is_expired == False
```

**Unit Tests**:
- Test expiration estimation for specific ingredient categories
- Test match percentage calculation with example pantries
- Test empty pantry edge cases

#### 4. Frontend Component Tests (Property-Based + Unit)

**Focus**: UI rendering, state management, user interactions

**Properties to Test**:
- Property 9: Pantry Display Completeness
- Property 10: Expiring Item Visual Highlighting
- Property 17: Recipe Step Display Completeness
- Property 21: Upload Loading Indicator Display
- Property 22: Error Message Display

**Example (using fast-check + React Testing Library)**:
```typescript
// Feature: rasoi-kitchen-intelligence, Property 9: Pantry Display Completeness
import fc from 'fast-check';
import { render, screen } from '@testing-library/react';

test('pantry displays all items', () => {
  fc.assert(
    fc.property(
      fc.array(pantryItemArbitrary(), { minLength: 1, maxLength: 20 }),
      (items) => {
        render(<PantryView items={items} onUpdateItem={jest.fn()} onDeleteItem={jest.fn()} />);
        
        // Assert all items are rendered
        items.forEach(item => {
          expect(screen.getByText(item.name)).toBeInTheDocument();
          expect(screen.getByText(item.quantity.toString())).toBeInTheDocument();
          expect(screen.getByText(item.unit)).toBeInTheDocument();
        });
      }
    ),
    { numRuns: 100 }
  );
});

// Arbitrary generator for pantry items
function pantryItemArbitrary(): fc.Arbitrary<PantryItem> {
  return fc.record({
    id: fc.uuid(),
    name: fc.string({ minLength: 3, maxLength: 50 }),
    quantity: fc.float({ min: 0.1, max: 100 }),
    unit: fc.constantFrom('g', 'kg', 'ml', 'l', 'cup', 'unit'),
    acquisitionDate: fc.date().map(d => d.toISOString()),
    expirationDate: fc.date().map(d => d.toISOString()),
    isExpiring: fc.boolean(),
    isExpired: fc.boolean()
  });
}
```

**Unit Tests**:
- Test navigation between routes
- Test Chammach animation triggering
- Test form submission and validation
- Test image upload file type validation

#### 5. API Endpoint Tests (Integration + Unit)

**Focus**: Request validation, response formatting, error handling

**Properties to Test**:
- Property 11: Vision Response Field Validation
- Property 19: Request Payload Validation

**Example**:
```python
# Feature: rasoi-kitchen-intelligence, Property 19: Request Payload Validation
@given(
    name=st.text(min_size=1, max_size=100),
    quantity=st.one_of(st.floats(min_value=0.1), st.integers(), st.text()),
    unit=st.text(max_size=20)
)
@pytest.mark.asyncio
async def test_pantry_update_validation(name, quantity, unit):
    """Test that pantry update endpoint validates request payloads."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            f"/api/pantry/test-id",
            json={"name": name, "quantity": quantity, "unit": unit}
        )
        
        # Should accept valid quantities, reject invalid
        if isinstance(quantity, (int, float)) and quantity > 0:
            assert response.status_code in [200, 404]  # 404 if item doesn't exist
        else:
            assert response.status_code == 422
            assert "validation" in response.json()["error"].lower()
```

**Integration Tests** (using mocked Claude APIs):
- Test POST /api/scan with various image types
- Test GET /api/recipes with different pantry states
- Test POST /api/substitute with missing ingredients
- Test error responses for API failures
- Test rate limit handling

#### 6. Claude Client Tests (Mock-Based Integration)

**Focus**: API integration, retry logic, error handling

**Tests**:
- Mock successful Vision API responses
- Mock rate limit errors with retry
- Mock network failures
- Mock malformed API responses
- Verify correct prompt construction
- Verify authentication headers

**Example**:
```python
@pytest.mark.asyncio
async def test_vision_client_retry_on_rate_limit():
    """Test that Vision client retries on rate limit errors."""
    client = ClaudeVisionClient(api_key="test-key", max_retries=2)
    
    with mock.patch.object(client.client.messages, 'create') as mock_create:
        # First two calls raise rate limit, third succeeds
        mock_create.side_effect = [
            anthropic.RateLimitError("Rate limited", status_code=429),
            anthropic.RateLimitError("Rate limited", status_code=429),
            anthropic.types.Message(content="success", model="claude-4")
        ]
        
        result = await client.analyze_image(b"fake-image", "test prompt")
        
        assert mock_create.call_count == 3
        assert result.content == "success"
```

### Test Organization

```
tests/
├── unit/
│   ├── parsers/
│   │   ├── test_ingredient_parser.py      # Properties 1, 12
│   │   ├── test_recipe_parser.py          # Properties 2, 13
│   │   └── test_substitution_parser.py    # Property 15
│   ├── repositories/
│   │   └── test_pantry_repository.py      # Properties 3, 4, 5, 6, 23
│   ├── services/
│   │   ├── test_pantry_service.py         # Properties 7, 8
│   │   ├── test_recipe_service.py         # Properties 14, 20
│   │   └── test_scanner_service.py
│   └── validators/
│       └── test_request_validation.py     # Properties 11, 19
├── integration/
│   ├── test_api_endpoints.py              # All endpoints
│   ├── test_claude_clients.py             # Claude API integration
│   └── test_database.py                   # Database operations
└── frontend/
    ├── components/
    │   ├── test_pantry_view.tsx           # Properties 9, 10
    │   ├── test_recipe_view.tsx           # Properties 16, 17
    │   ├── test_scanner.tsx               # Property 21
    │   └── test_chammach.tsx              # Property 18
    └── integration/
        └── test_api_service.tsx           # Property 22
```

### Coverage Targets

- **Parser Layer**: 100% line coverage (pure functions, highly testable)
- **Repository Layer**: 95% line coverage
- **Service Layer**: 90% line coverage
- **API Endpoints**: 85% line coverage
- **Frontend Components**: 80% line coverage

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest hypothesis pytest-cov pytest-asyncio
      - name: Run property-based tests
        run: pytest tests/unit --hypothesis-seed=random -v --cov=src
      - name: Run integration tests
        run: pytest tests/integration -v
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test -- --coverage --watchAll=false
```

### Manual Testing Scenarios

#### Hackathon Demo Script

1. **Happy Path**: Upload clear ingredient photo → View pantry → Get recommendations → Cook recipe
2. **Receipt Upload**: Upload grocery receipt → Verify multiple items extracted → Check expiration dates
3. **Expiring Items**: Add items expiring in 2 days → Verify visual highlighting → Check recipe prioritization
4. **Missing Ingredients**: Select recipe with missing items → Request substitutions → View alternatives
5. **Error Scenarios**: Upload invalid file type → Upload very large file → Test with no internet connection
6. **Chammach Guidance**: Navigate through all views → Verify contextual messages appear

#### Performance Testing

- Measure image upload and processing time (target: < 5 seconds)
- Test with 50+ pantry items (target: < 500ms render time)
- Test recipe generation with 20+ ingredients (target: < 8 seconds)
- Verify loading indicators appear within 100ms of action

### Test Data

#### Sample Ingredients

```python
SAMPLE_INGREDIENTS = [
    {"name": "Milk", "quantity": 1.0, "unit": "l", "days_until_expiry": 2},
    {"name": "Eggs", "quantity": 12, "unit": "unit", "days_until_expiry": 7},
    {"name": "Tomatoes", "quantity": 500, "unit": "g", "days_until_expiry": 3},
    {"name": "Chicken Breast", "quantity": 600, "unit": "g", "days_until_expiry": 1},
    {"name": "Rice", "quantity": 2, "unit": "kg", "days_until_expiry": 365},
]
```

#### Sample Recipes

```json
{
  "name": "Chicken Fried Rice",
  "ingredients": [
    {"name": "Chicken Breast", "quantity": 300, "unit": "g"},
    {"name": "Rice", "quantity": 200, "unit": "g"},
    {"name": "Eggs", "quantity": 2, "unit": "unit"}
  ],
  "steps": [
    "Cook rice and let cool",
    "Dice chicken and stir-fry until golden",
    "Add eggs and scramble",
    "Mix in rice and season"
  ],
  "prep_time_minutes": 25
}
```

