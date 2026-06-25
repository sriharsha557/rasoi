# Requirements Document

## Introduction

RasOI is a multimodal AI-powered kitchen intelligence web application designed to reduce food waste through intelligent pantry management. The system enables users to scan ingredients via photos or grocery receipts to build and maintain a live pantry inventory. RasOI detects expiring items and recommends meals that maximize ingredient usage while providing intelligent substitution suggestions and interactive cooking guidance through an animated mascot (Chammach the talking spoon).

The application targets hackathon demonstration with a 12-hour build timeline, prioritizing core functionality and user experience over comprehensive feature coverage.

## Glossary

- **RasOI_System**: The complete web application including frontend, backend, and AI services
- **Pantry_Inventory**: The user's current collection of ingredients with expiration dates and quantities
- **Ingredient_Scanner**: The multimodal input component that processes photos and receipt images
- **Vision_AI**: Claude Sonnet 4 Vision API for image analysis
- **Text_AI**: Claude Sonnet 4 Text API for recipe and recommendation generation
- **Meal_Recommender**: The component that suggests recipes based on available ingredients
- **Substitution_Engine**: The component that suggests ingredient alternatives
- **Chammach**: The animated talking spoon mascot that provides contextual guidance
- **Expiring_Item**: An ingredient within 3 days of expiration date
- **Recipe_View**: The step-by-step cooking interface
- **Frontend**: React application with Tailwind CSS
- **Backend**: FastAPI service layer
- **User**: Person interacting with the RasOI application

## Requirements

### Requirement 1: Multimodal Ingredient Input

**User Story:** As a User, I want to scan ingredients using photos or grocery receipts, so that I can quickly build my pantry inventory without manual data entry.

#### Acceptance Criteria

1. WHEN a User uploads an ingredient photo, THE Ingredient_Scanner SHALL extract ingredient names, quantities, and estimated expiration dates
2. WHEN a User uploads a grocery receipt image, THE Ingredient_Scanner SHALL extract purchased items with dates and quantities
3. THE Ingredient_Scanner SHALL send images to Vision_AI for analysis
4. WHEN Vision_AI returns parsed data, THE Ingredient_Scanner SHALL validate the extracted fields contain ingredient name and acquisition date
5. IF Vision_AI fails to parse an image, THEN THE RasOI_System SHALL return an error message describing the parsing failure
6. FOR ALL valid ingredient extractions, parsing the Vision_AI response then formatting for storage then parsing again SHALL produce equivalent ingredient data (round-trip property)

### Requirement 2: Pantry Inventory Management

**User Story:** As a User, I want to view and manage my live pantry inventory, so that I can track what ingredients I have available.

#### Acceptance Criteria

1. THE Pantry_Inventory SHALL store ingredient name, quantity, acquisition date, and expiration date for each item
2. WHEN a User adds an ingredient, THE Pantry_Inventory SHALL accept the ingredient data and persist it
3. WHEN a User views the pantry, THE Frontend SHALL display all ingredients with their quantities and expiration dates
4. WHEN a User removes an ingredient, THE Pantry_Inventory SHALL delete the ingredient from storage
5. WHEN a User updates an ingredient quantity, THE Pantry_Inventory SHALL modify the stored quantity value
6. THE Frontend SHALL sort ingredients by expiration date with earliest dates displayed first
7. FOR ALL Pantry_Inventory operations, the total count of unique ingredients SHALL remain consistent with add and remove operations

### Requirement 3: Expiration Detection and Alerts

**User Story:** As a User, I want to be alerted about expiring ingredients, so that I can use them before they spoil.

#### Acceptance Criteria

1. WHEN the RasOI_System calculates expiration status, THE RasOI_System SHALL identify items expiring within 3 days as Expiring_Items
2. WHEN a User views the Pantry_Inventory, THE Frontend SHALL visually highlight Expiring_Items with warning indicators
3. THE RasOI_System SHALL check expiration dates against the current system date
4. WHEN multiple items are expiring, THE Frontend SHALL display them in order from soonest to latest expiration
5. WHEN an ingredient expires (expiration date is in the past), THE Frontend SHALL mark the ingredient as expired with distinct visual styling

### Requirement 4: Smart Meal Recommendations

**User Story:** As a User, I want to receive meal recommendations based on my available ingredients, so that I can maximize ingredient usage and reduce waste.

#### Acceptance Criteria

1. WHEN a User requests meal recommendations, THE Meal_Recommender SHALL analyze the Pantry_Inventory and prioritize Expiring_Items
2. THE Meal_Recommender SHALL send the ingredient list to Text_AI for recipe generation
3. WHEN Text_AI returns recipes, THE Meal_Recommender SHALL present recipes that use the maximum number of available ingredients
4. WHEN generating recommendations, THE Meal_Recommender SHALL prioritize recipes using Expiring_Items over non-expiring items
5. THE Meal_Recommender SHALL return recipe name, ingredient list, cooking steps, and estimated preparation time for each recommendation
6. WHEN insufficient ingredients exist for a complete recipe, THE Meal_Recommender SHALL include the recipe with missing ingredients clearly indicated

### Requirement 5: Intelligent Substitution Engine

**User Story:** As a User, I want to receive ingredient substitution suggestions, so that I can cook recipes even when missing specific ingredients.

#### Acceptance Criteria

1. WHEN a recipe requires unavailable ingredients, THE Substitution_Engine SHALL identify available alternatives from the Pantry_Inventory
2. THE Substitution_Engine SHALL send substitution requests to Text_AI with context about the recipe and available ingredients
3. WHEN Text_AI returns substitution suggestions, THE Substitution_Engine SHALL present alternatives with substitution ratios
4. THE Substitution_Engine SHALL suggest substitutions that maintain recipe compatibility
5. WHEN no suitable substitution exists in the Pantry_Inventory, THE Substitution_Engine SHALL indicate the ingredient must be acquired

### Requirement 6: Step-by-Step Recipe View

**User Story:** As a User, I want to follow recipes in a step-by-step format, so that I can cook efficiently without losing my place.

#### Acceptance Criteria

1. WHEN a User selects a recipe, THE Recipe_View SHALL display the first cooking step
2. THE Recipe_View SHALL provide navigation controls to move forward and backward through steps
3. WHEN a User navigates to a step, THE Recipe_View SHALL display the step instructions, required ingredients, and timing information
4. THE Recipe_View SHALL maintain the current step position when the User temporarily navigates away
5. WHEN a User completes the final step, THE Recipe_View SHALL display a completion message

### Requirement 7: Chammach Mascot Integration

**User Story:** As a User, I want contextual guidance from an animated mascot, so that I have an engaging and helpful cooking experience.

#### Acceptance Criteria

1. THE Frontend SHALL display Chammach as an animated talking spoon character
2. WHEN a User views the Pantry_Inventory, THE Chammach SHALL provide tips about Expiring_Items
3. WHEN a User views meal recommendations, THE Chammach SHALL explain why specific recipes were suggested
4. WHEN a User views the Recipe_View, THE Chammach SHALL provide cooking tips relevant to the current step
5. THE Chammach SHALL animate when delivering messages to the User
6. WHEN no contextual guidance is needed, THE Chammach SHALL display in an idle animation state

### Requirement 8: Frontend User Interface

**User Story:** As a User, I want a responsive and intuitive interface, so that I can efficiently interact with the application.

#### Acceptance Criteria

1. THE Frontend SHALL implement a React application with Tailwind CSS styling
2. THE Frontend SHALL provide navigation between Ingredient_Scanner, Pantry_Inventory, Meal_Recommender, and Recipe_View screens
3. WHEN a User uploads an image, THE Frontend SHALL display a loading indicator during processing
4. WHEN the Backend returns data, THE Frontend SHALL update the interface within 500 milliseconds
5. THE Frontend SHALL display error messages when operations fail
6. THE Frontend SHALL be responsive on desktop and tablet screen sizes

### Requirement 9: Backend API Services

**User Story:** As a Developer, I want a FastAPI backend service, so that the Frontend can communicate with AI services and data storage.

#### Acceptance Criteria

1. THE Backend SHALL implement a FastAPI application with REST endpoints
2. THE Backend SHALL provide endpoints for ingredient upload, pantry management, meal recommendations, and substitution requests
3. WHEN the Backend receives an image upload, THE Backend SHALL forward the image to Vision_AI within 1 second
4. WHEN the Backend receives a recommendation request, THE Backend SHALL query Text_AI with the current Pantry_Inventory
5. THE Backend SHALL validate all incoming request payloads before processing
6. IF request validation fails, THEN THE Backend SHALL return a 400 status code with validation error details
7. THE Backend SHALL handle Vision_AI and Text_AI rate limits gracefully with appropriate error responses

### Requirement 10: AI Service Integration

**User Story:** As a Developer, I want integration with Claude Sonnet 4 Vision and Text APIs, so that the application can process images and generate recommendations.

#### Acceptance Criteria

1. THE Backend SHALL authenticate with Claude Sonnet 4 API using secure credentials
2. WHEN processing images, THE Backend SHALL use Vision_AI for optical character recognition and object detection
3. WHEN generating recipes or substitutions, THE Backend SHALL use Text_AI with structured prompts
4. THE Backend SHALL parse Vision_AI responses into structured ingredient data
5. THE Backend SHALL parse Text_AI responses into structured recipe and substitution data
6. IF an AI service request fails, THEN THE Backend SHALL retry the request up to 2 additional times
7. IF all retry attempts fail, THEN THE Backend SHALL return an error to the Frontend

### Requirement 11: Data Persistence

**User Story:** As a User, I want my pantry data to persist across sessions, so that I don't lose my inventory when closing the application.

#### Acceptance Criteria

1. THE Backend SHALL store Pantry_Inventory data in persistent storage
2. WHEN a User adds or modifies ingredients, THE Backend SHALL save changes to persistent storage within 2 seconds
3. WHEN a User returns to the application, THE Backend SHALL load the Pantry_Inventory from persistent storage
4. THE Backend SHALL maintain data integrity during concurrent operations
5. FOR ALL storage operations, writing data then reading it back SHALL produce equivalent data (round-trip property)

### Requirement 12: Vision AI Response Parser

**User Story:** As a Developer, I want to parse Vision AI responses reliably, so that ingredient data is accurately extracted from images.

#### Acceptance Criteria

1. THE Backend SHALL implement a Parser for Vision_AI JSON responses
2. WHEN Vision_AI returns ingredient data, THE Parser SHALL extract ingredient name, quantity, unit, and date fields
3. THE Parser SHALL implement a Pretty_Printer to format ingredient data back into Vision_AI compatible JSON
4. FOR ALL valid Vision_AI responses, parsing then pretty-printing then parsing SHALL produce equivalent ingredient objects (round-trip property)
5. IF the Vision_AI response contains malformed JSON, THEN THE Parser SHALL return a descriptive parsing error

### Requirement 13: Recipe Response Parser

**User Story:** As a Developer, I want to parse recipe responses from Text AI reliably, so that recipes are consistently structured for display.

#### Acceptance Criteria

1. THE Backend SHALL implement a Parser for Text_AI recipe responses
2. WHEN Text_AI returns recipe data, THE Parser SHALL extract recipe name, ingredients list, steps array, and preparation time
3. THE Parser SHALL implement a Pretty_Printer to format recipe data back into Text_AI compatible format
4. FOR ALL valid recipe responses, parsing then pretty-printing then parsing SHALL produce equivalent recipe objects (round-trip property)
5. IF the Text_AI response contains incomplete recipe data, THEN THE Parser SHALL return a descriptive parsing error
