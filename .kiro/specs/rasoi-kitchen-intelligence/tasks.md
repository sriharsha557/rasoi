# Implementation Plan: RasOI Kitchen Intelligence

## Overview

This implementation plan converts the RasOI feature design into executable coding tasks. The application is a multimodal AI-powered kitchen intelligence web application with React + TypeScript frontend, FastAPI + Python backend, and Claude Sonnet 4 Vision and Text API integrations.

The tasks are organized to enable incremental development with early validation checkpoints. Each task builds on previous work, and all components are integrated progressively to avoid orphaned code.

## Tasks

- [x] 1. Initialize project structure and development environment
  - Create monorepo structure with separate `frontend/` and `backend/` directories
  - Initialize React TypeScript project with Vite in `frontend/`
  - Initialize Python FastAPI project in `backend/` with virtual environment
  - Set up Tailwind CSS configuration in frontend
  - Configure environment variables for Anthropic API keys
  - Create `.gitignore` for both frontend and backend
  - Set up `requirements.txt` with FastAPI, Pydantic, Anthropic SDK, SQLite3, httpx
  - Set up `package.json` with React, TypeScript, React Router, Axios, Tailwind CSS
  - _Requirements: 8.1, 9.1_

- [ ] 2. Implement backend data models and database layer
  - [ ] 2.1 Define Pydantic data models
    - Create `backend/models.py` with all Pydantic models: `Ingredient`, `PantryItem`, `PantryItemUpdate`, `RecipeIngredient`, `Recipe`, `Substitution`, `VisionResponse`, `TextResponse`, `ScanType` enum
    - Implement `is_expiring` and `is_expired` computed properties on `PantryItem`
    - Add field validation constraints (quantity >= 0, confidence 0-1, match_percentage 0-100)
    - _Requirements: 2.1, 3.1, 3.5_
  
  - [ ] 2.2 Create database schema and repository
    - Create `backend/database.py` with SQLite connection management
    - Define `pantry_items` table schema with indexes on `expiration_date` and `name`
    - Create trigger for automatic `updated_at` timestamp updates
    - Implement `PantryRepository` class with async methods: `create`, `get_all`, `get_by_id`, `update`, `delete`
    - _Requirements: 11.1, 11.2, 11.3_
  
  - [ ]* 2.3 Write property test for storage round-trip
    - **Property 3: Storage Round-Trip**
    - **Validates: Requirements 11.5**
    - Generate random valid `PantryItem` instances
    - Write to repository, read back, assert equivalence
    - Test with edge cases: minimum/maximum quantities, boundary dates

- [ ] 3. Checkpoint - Database layer validation
  - Ensure all tests pass, verify database schema created correctly
  - Test CRUD operations manually with sample data
  - Ask the user if questions arise

- [ ] 4. Implement AI client layer
  - [ ] 4.1 Create Claude Vision API client
    - Create `backend/clients/vision_client.py` with `ClaudeVisionClient` class
    - Implement `__init__` with API key and retry configuration
    - Implement `analyze_image` method with retry logic and error handling
    - Implement `build_ingredient_prompt` and `build_receipt_prompt` methods
    - Add custom exception `VisionAPIError` for API failures
    - _Requirements: 10.1, 10.2, 10.6_
  
  - [ ] 4.2 Create Claude Text API client
    - Create `backend/clients/text_client.py` with `ClaudeTextClient` class
    - Implement `__init__` with API key and retry configuration
    - Implement `generate_recipes` method with structured prompt building
    - Implement `generate_substitutions` method with context-aware prompts
    - Add custom exception `TextAPIError` for API failures
    - _Requirements: 10.1, 10.3, 10.6_

- [ ] 5. Implement parser utilities
  - [ ] 5.1 Create ingredient parser
    - Create `backend/parsers/ingredient_parser.py` with `IngredientParser` class
    - Implement `parse` static method to convert Vision API JSON to `Ingredient` list
    - Implement `pretty_print` static method to serialize `Ingredient` list to JSON
    - Handle malformed JSON with descriptive errors
    - _Requirements: 12.1, 12.2, 12.5_
  
  - [ ]* 5.2 Write property test for Vision parser round-trip
    - **Property 1: Vision Parser Round-Trip**
    - **Validates: Requirements 1.6, 12.4**
    - Generate valid Vision API JSON responses with varied ingredient data
    - Parse → pretty_print → parse, assert equivalence
    - Test with edge cases: missing optional fields, special characters in names
  
  - [ ] 5.3 Create recipe parser
    - Create `backend/parsers/recipe_parser.py` with `RecipeParser` class
    - Implement `parse` static method to convert Text API JSON to `Recipe` list
    - Implement `pretty_print` static method to serialize `Recipe` list to JSON
    - Handle incomplete recipe data with descriptive errors
    - _Requirements: 13.1, 13.2, 13.5_
  
  - [ ]* 5.4 Write property test for recipe parser round-trip
    - **Property 2: Recipe Parser Round-Trip**
    - **Validates: Requirements 13.4**
    - Generate valid Text API recipe JSON with varied recipe structures
    - Parse → pretty_print → parse, assert equivalence
    - Test with multiple ingredients, varying step counts
  
  - [ ] 5.5 Create substitution parser
    - Create `backend/parsers/substitution_parser.py` with `SubstitutionParser` class
    - Implement `parse` static method to convert Text API JSON to `Substitution` list
    - Implement `pretty_print` static method to serialize `Substitution` list to JSON
    - _Requirements: 5.3, 10.5_

- [ ] 6. Checkpoint - Parser layer validation
  - Ensure all parser tests pass
  - Manually test parsers with sample Claude API responses
  - Ask the user if questions arise

- [ ] 7. Implement backend service layer
  - [ ] 7.1 Create scanner service
    - Create `backend/services/scanner_service.py` with `ScannerService` class
    - Implement `scan_image` method coordinating Vision API call, parsing, enrichment, storage
    - Implement `estimate_expiration` method with hardcoded ingredient category lookup
    - Add image validation (format, size constraints)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 7.2 Create pantry service
    - Create `backend/services/pantry_service.py` with `PantryService` class
    - Implement `get_all_items` with expiration status computation
    - Implement `add_item`, `update_item`, `delete_item` delegating to repository
    - Implement `get_expiring_items` filtering items within N days
    - _Requirements: 2.2, 2.4, 2.5, 3.1_
  
  - [ ]* 7.3 Write property tests for pantry service operations
    - **Property 4: Ingredient Addition Persistence**
    - **Validates: Requirements 2.2**
    - Add random valid ingredients, verify retrieval by ID
    - **Property 5: Ingredient Deletion Completeness**
    - **Validates: Requirements 2.4**
    - Add items, delete by ID, verify not retrievable and absent from list
    - **Property 6: Quantity Update Persistence**
    - **Validates: Requirements 2.5**
    - Update quantities, verify new values persist
  
  - [ ]* 7.4 Write property tests for sorting and expiration detection
    - **Property 7: Expiration Date Sorting**
    - **Validates: Requirements 2.6, 3.4**
    - Generate random items with varied dates, sort, verify order
    - **Property 8: Expiring Item Detection**
    - **Validates: Requirements 3.1, 3.5**
    - Generate items with dates ranging from past to future, verify expiring/expired flags
  
  - [ ] 7.5 Create recipe service
    - Create `backend/services/recipe_service.py` with `RecipeService` class
    - Implement `get_recommendations` coordinating pantry fetch, prompt building, Text API call, parsing
    - Implement `calculate_match_percentage` computing available ingredient ratio
    - Prioritize expiring items in prompt construction
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_
  
  - [ ]* 7.6 Write property test for recipe ingredient matching
    - **Property 14: Recipe Ingredient Matching**
    - **Validates: Requirements 4.6**
    - Generate recipes with N ingredients, pantries with M ingredients
    - Verify match percentage = (available / N) × 100
    - Verify missing ingredients are correctly identified
  
  - [ ] 7.7 Create substitution service
    - Create `backend/services/substitution_service.py` with `SubstitutionService` class
    - Implement `get_substitutions` building context-aware prompts with available ingredients
    - Parse substitution responses and flag available alternatives
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8. Checkpoint - Service layer validation
  - Run all service layer property tests
  - Manually test services with mock AI responses
  - Ask the user if questions arise

- [ ] 9. Implement FastAPI backend routes
  - [ ] 9.1 Create API router and main application
    - Create `backend/main.py` with FastAPI app initialization
    - Configure CORS middleware for frontend communication
    - Set up dependency injection for services and database
    - _Requirements: 9.1, 9.5_
  
  - [ ] 9.2 Implement scan endpoint
    - Create `backend/routers/scan.py` with `POST /api/scan` endpoint
    - Accept multipart form data with image file and scan type
    - Call `ScannerService.scan_image`
    - Return structured response with ingredients list
    - Handle errors with appropriate status codes (400, 422, 500)
    - _Requirements: 1.5, 9.3, 9.6, 9.7_
  
  - [ ] 9.3 Implement pantry endpoints
    - Create `backend/routers/pantry.py` with pantry CRUD endpoints
    - `GET /api/pantry` - retrieve all items
    - `PUT /api/pantry/{item_id}` - update item
    - `DELETE /api/pantry/{item_id}` - delete item
    - Add request validation with Pydantic models
    - _Requirements: 2.3, 2.4, 2.5, 9.5_
  
  - [ ] 9.4 Implement recipe endpoints
    - Create `backend/routers/recipes.py` with `GET /api/recipes` endpoint
    - Accept query parameters: `prioritize_expiring`, `max_recipes`
    - Call `RecipeService.get_recommendations`
    - Return recipes sorted by match percentage
    - _Requirements: 4.1, 4.2, 4.3, 9.4_
  
  - [ ] 9.5 Implement substitution endpoint
    - Create `backend/routers/substitutions.py` with `POST /api/substitute` endpoint
    - Accept request body with recipe ID, missing ingredient, recipe context
    - Call `SubstitutionService.get_substitutions`
    - Return substitution suggestions with availability flags
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ] 9.6 Implement health check endpoint
    - Create `backend/routers/health.py` with `GET /api/health` endpoint
    - Check database connection status
    - Check Claude API connectivity (optional ping)
    - Return service status and timestamp
    - _Requirements: 9.2_

- [ ] 10. Checkpoint - Backend API validation
  - Test all API endpoints with Postman or curl
  - Verify error handling for invalid requests
  - Verify Claude API integration with real API calls
  - Ask the user if questions arise

- [ ] 11. Implement frontend data models and API client
  - [ ] 11.1 Define TypeScript interfaces
    - Create `frontend/src/types/index.ts` with all interfaces: `PantryItem`, `Ingredient`, `Recipe`, `RecipeIngredient`, `Substitution`, `ChammachMessage`
    - _Requirements: 2.1, 4.5_
  
  - [ ] 11.2 Create Axios API client
    - Create `frontend/src/services/apiClient.ts` with Axios instance
    - Configure base URL pointing to FastAPI backend
    - Implement API methods: `scanImage`, `getPantry`, `updatePantryItem`, `deletePantryItem`, `getRecipes`, `getSubstitutions`, `healthCheck`
    - Add error handling and response transformations
    - _Requirements: 8.3, 9.2_

- [ ] 12. Implement frontend React context and state management
  - [ ] 12.1 Create pantry context
    - Create `frontend/src/context/PantryContext.tsx` with React Context + useReducer
    - Define state shape: `pantryItems`, `isLoading`, `error`
    - Implement actions: `ADD_ITEMS`, `UPDATE_ITEM`, `DELETE_ITEM`, `SET_LOADING`, `SET_ERROR`
    - Create `PantryProvider` component wrapping the app
    - _Requirements: 2.3, 8.4_
  
  - [ ] 12.2 Create recipe context
    - Create `frontend/src/context/RecipeContext.tsx` for recipe state
    - Define state shape: `recipes`, `currentRecipe`, `currentStep`, `isLoading`
    - Implement actions: `SET_RECIPES`, `SELECT_RECIPE`, `NEXT_STEP`, `PREV_STEP`
    - _Requirements: 4.3, 6.4_

- [ ] 13. Implement frontend core components
  - [ ] 13.1 Create Scanner component
    - Create `frontend/src/components/Scanner.tsx`
    - Implement drag-and-drop file upload with react-dropzone or native HTML5
    - Display image preview before upload
    - Show loading spinner during scan processing
    - Validate file type (JPEG, PNG) and size (max 5MB)
    - Call `apiClient.scanImage` and update pantry context on success
    - Display error messages on failure
    - _Requirements: 1.1, 1.2, 1.5, 8.3_
  
  - [ ]* 13.2 Write unit tests for Scanner component
    - Test file validation logic
    - Test upload success and error handling
    - Mock API client responses
  
  - [ ] 13.3 Create PantryView component
    - Create `frontend/src/components/PantryView.tsx`
    - Fetch pantry items from context
    - Display items in a list/table sorted by expiration date
    - Implement inline quantity editing with debounced API calls
    - Add delete button with confirmation modal
    - Show empty state when no items exist
    - _Requirements: 2.3, 2.4, 2.5, 2.6_
  
  - [ ]* 13.4 Write property tests for pantry display
    - **Property 9: Pantry Display Completeness**
    - **Validates: Requirements 2.3**
    - Render with N items, verify all N rendered with name, quantity, unit, expiration
    - **Property 10: Expiring Item Visual Highlighting**
    - **Validates: Requirements 3.2, 3.5**
    - Render items with expiring/expired flags, verify distinct CSS classes applied
  
  - [ ] 13.5 Create RecipeList component
    - Create `frontend/src/components/RecipeList.tsx`
    - Display recipe cards with name, prep time, match percentage
    - Show badge for recipes using expiring items
    - Implement click handler to navigate to RecipeView
    - Show loading state while fetching recommendations
    - _Requirements: 4.3, 4.4, 4.6_
  
  - [ ] 13.6 Create RecipeView component
    - Create `frontend/src/components/RecipeView.tsx`
    - Display current recipe step with large readable text
    - Show progress indicator (Step X of Y)
    - Implement next/previous navigation buttons
    - Display ingredient list with availability indicators
    - Show substitution button for missing ingredients
    - Persist current step in recipe context
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ]* 13.7 Write property test for recipe step navigation state
    - **Property 16: Recipe Step Navigation State**
    - **Validates: Requirements 6.4**
    - Set step position, navigate away, return, verify position restored

- [ ] 14. Implement Chammach mascot component
  - [ ] 14.1 Create Chammach component with animations
    - Create `frontend/src/components/Chammach.tsx`
    - Implement CSS animations or integrate Lottie for spoon character
    - Add speech bubble with dynamic text
    - Support different animation states: idle, pantry, recipes, cooking
    - _Requirements: 7.1, 7.5, 7.6_
  
  - [ ] 14.2 Add contextual messaging logic
    - Create `frontend/src/utils/chammachMessages.ts` with context-aware message generator
    - Return different messages based on context: pantry tips, recipe explanations, cooking guidance
    - Integrate Chammach into PantryView, RecipeList, RecipeView components
    - _Requirements: 7.2, 7.3, 7.4_

- [ ] 15. Implement frontend routing and navigation
  - [ ] 15.1 Set up React Router
    - Create `frontend/src/App.tsx` with BrowserRouter
    - Define routes: `/` (Scanner), `/pantry` (PantryView), `/recipes` (RecipeList), `/recipe/:id` (RecipeView)
    - Create navigation header with links
    - _Requirements: 8.2_
  
  - [ ] 15.2 Add loading and error states
    - Create `frontend/src/components/LoadingSpinner.tsx`
    - Create `frontend/src/components/ErrorMessage.tsx`
    - Integrate loading spinner for API calls
    - Display error messages with retry options
    - _Requirements: 8.3, 8.4, 8.5_

- [ ] 16. Implement styling and responsiveness
  - [ ] 16.1 Apply Tailwind CSS styling to all components
    - Style Scanner with centered upload area and drag-drop effects
    - Style PantryView with table/card layout and expiration color coding
    - Style RecipeList with card grid layout
    - Style RecipeView with large step text and navigation controls
    - Style Chammach with positioned speech bubble
    - _Requirements: 8.1, 8.6_
  
  - [ ] 16.2 Add visual indicators for expiring items
    - Apply warning colors (yellow/orange) for expiring items (within 3 days)
    - Apply danger colors (red) for expired items
    - Add icons or badges for visual prominence
    - _Requirements: 3.2, 3.5_
  
  - [ ] 16.3 Ensure responsive design
    - Test and adjust layouts for desktop (1920x1080), tablet (768x1024)
    - Use Tailwind responsive breakpoints (sm, md, lg)
    - Ensure touch-friendly controls on tablet
    - _Requirements: 8.6_

- [ ] 17. Checkpoint - Frontend integration validation
  - Test full user flows: scan → pantry → recipes → cooking
  - Verify frontend-backend communication
  - Test error handling and edge cases
  - Ask the user if questions arise

- [ ] 18. Implement field validation and error handling
  - [ ] 18.1 Add Vision API response validation
    - Create `backend/validators/vision_validator.py`
    - Implement validation checking required fields: ingredient name, acquisition date
    - Reject responses missing required fields with descriptive errors
    - _Requirements: 1.4, 12.1_
  
  - [ ]* 18.2 Write property test for Vision response field validation
    - **Property 11: Vision Response Field Validation**
    - **Validates: Requirements 1.4**
    - Generate responses with/without required fields, verify accept/reject behavior
  
  - [ ] 18.3 Add recipe response validation
    - Implement validation for recipe name, ingredients list, steps array, prep time
    - Reject incomplete recipes with descriptive errors
    - _Requirements: 4.5, 13.1_
  
  - [ ]* 18.4 Write property test for recipe field extraction
    - **Property 13: Recipe Field Extraction**
    - **Validates: Requirements 4.5, 13.2**
    - Generate valid recipe responses, verify all fields extracted correctly

- [ ] 19. Integration and final wiring
  - [ ] 19.1 Wire all components together in App.tsx
    - Import all contexts, components, and routes
    - Ensure state flows correctly between components
    - Add global error boundary for unhandled errors
    - _Requirements: 8.1, 8.2_
  
  - [ ] 19.2 Configure environment variables
    - Create `.env` files for frontend (API base URL) and backend (Anthropic API key, database path)
    - Add `.env.example` templates with dummy values
    - Document required environment variables in README
    - _Requirements: 10.1_
  
  - [ ] 19.3 Add development scripts
    - Add `npm run dev` script for frontend development server
    - Add `uvicorn` command for backend development server with hot reload
    - Document startup instructions in README
    - _Requirements: 9.1_
  
  - [ ]* 19.4 Write integration tests
    - Test full scan → pantry → recipes flow with mocked AI responses
    - Test substitution flow with missing ingredients
    - Test error scenarios: API failures, invalid uploads, network errors

- [ ] 20. Final checkpoint and documentation
  - Run all property tests and unit tests
  - Perform end-to-end manual testing of all user flows
  - Verify Chammach animations and contextual messages
  - Create README with setup instructions, API documentation, and architecture overview
  - Ensure all environment variables documented
  - Ask the user if questions arise or if any refinements needed

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and provide natural pause points
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation follows a bottom-up approach: data layer → service layer → API layer → frontend layer
- Early checkpoints catch issues before building dependent layers
- All parsers implement round-trip properties to ensure data integrity
- Frontend and backend can be developed in parallel after API contract is defined (Task 9)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3"] },
    { "id": 3, "tasks": ["4.1", "4.2"] },
    { "id": 4, "tasks": ["5.1", "5.3", "5.5"] },
    { "id": 5, "tasks": ["5.2", "5.4"] },
    { "id": 6, "tasks": ["7.1", "7.2", "7.5", "7.7"] },
    { "id": 7, "tasks": ["7.3", "7.4", "7.6"] },
    { "id": 8, "tasks": ["9.1"] },
    { "id": 9, "tasks": ["9.2", "9.3", "9.4", "9.5", "9.6"] },
    { "id": 10, "tasks": ["11.1", "11.2"] },
    { "id": 11, "tasks": ["12.1", "12.2"] },
    { "id": 12, "tasks": ["13.1", "13.3", "13.5", "13.6"] },
    { "id": 13, "tasks": ["13.2", "13.4", "13.7"] },
    { "id": 14, "tasks": ["14.1", "14.2"] },
    { "id": 15, "tasks": ["15.1", "15.2"] },
    { "id": 16, "tasks": ["16.1", "16.2", "16.3"] },
    { "id": 17, "tasks": ["18.1", "18.3"] },
    { "id": 18, "tasks": ["18.2", "18.4"] },
    { "id": 19, "tasks": ["19.1", "19.2", "19.3"] },
    { "id": 20, "tasks": ["19.4"] }
  ]
}
```
