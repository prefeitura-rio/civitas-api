# Integration Test Plan for Cars Endpoints

## Current Status ✅ REFACTORED
- **Total integration tests**: 29 passing tests (UP FROM 21!)
  - `test_cars_endpoints.py`: 16 comprehensive cars endpoint tests (NEW CONSOLIDATED FILE!)
  - `test_working_integration.py`: 13 tests for various integration scenarios

## Next Steps - Cars Endpoints to Test

### 🎯 Completed Successfully ✅
1. **MAJOR REFACTORING**: Consolidated all cars tests into one clear file:
   - ❌ Removed: `test_cars_plate_endpoints.py` (4 tests)
   - ❌ Removed: `test_cars_simple.py` (4 tests) 
   - ✅ **NEW**: `test_cars_endpoints.py` (16 tests) - Much better organized!

2. **Cars Endpoints Now Covered** (16 tests total):
   - ✅ `GET /cars/plate/{plate}` - 4 tests (success, validation, 451 handling, caching)
   - ✅ `POST /cars/plates` - 3 tests (validation errors, malformed requests)
   - ✅ `GET /cars/hint` - 1 test (missing parameters validation)
   - ✅ `GET /cars/monitored` - 3 tests (basic request, validation errors)
   - ✅ `GET /cars/path` - 2 tests (missing/partial parameters)
   - ✅ `GET /cars/radar` - 1 test (missing parameters)
   - ✅ General validation - 2 tests (comprehensive plate format, error consistency)

3. **Better Test Organization**: 
   - ✅ Clear class-based organization by endpoint
   - ✅ Intuitive test names that describe what's being tested
   - ✅ Easy to find cars-related tests by filename

### 🚧 Attempted but Blocked
1. **Complex endpoint tests** with external API mocking
   - Issue: Endpoints make actual HTTP calls that bypass our mocks
   - Problem: Cache decorators and external service integrations are complex
   - **Lesson**: Start with validation-only tests first

### 🔮 Future Cars Endpoints to Consider
3. `GET /cars/monitored` - List monitored plates with filters
4. `POST /cars/monitored` - Create monitored plate
5. `GET /cars/monitored/{plate}` - Get specific monitored plate
6. `PUT /cars/monitored/{plate}` - Update monitored plate 
7. `DELETE /cars/monitored/{plate}` - Delete monitored plate
8. `GET /cars/path` - Get car path
9. `GET /cars/n_before_after` - Get plates before/after

### 📋 Testing Approach
- Start with one endpoint at a time
- Create simple, working test first
- Validate it passes before moving to next
- Use existing mocking patterns (patch app.utils functions)
- Follow valid plate formats (ABC1234 pattern)

### 🔧 Available Mocking Patterns
- `patch("app.utils.cortex_request")` for external API calls
- `patch("app.utils.get_hints")` for hint functionality
- `patch("app.utils.get_plate_details")` for plate details
- Valid plate formats: ABC1234, DEF5678, etc. (3 letters + 4 digits)