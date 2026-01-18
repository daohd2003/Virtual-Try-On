# HackAIThon - Virtual Try-On API
<img width="2703" height="2115" alt="image" src="https://github.com/user-attachments/assets/37b31934-fb64-425f-8011-6a6d859694da" />

A FastAPI application that allows users to virtually try on clothing items using AI. This API provides a comprehensive solution for fashion virtual try-on with AI-powered feedback.

## Features

- Upload images of people and clothing items
- AI-powered virtual try-on processing
- AI fashion feedback with style recommendations
- Image storage in Cloudinary
- PostgreSQL database with proper schema versioning
- User history management
- Comprehensive error handling

## Technology Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **Image Storage**: Cloudinary
- **Try-On Model**: CatVTON (Stable Diffusion-based model)
- **Fashion Feedback**: Google Gemini 2.0 Flash
- **Image Processing**: PIL, OpenCV
- **Deployment**: Uvicorn ASGI server

## System Architecture

The system follows a modular architecture:

1. **API Layer** (`main.py`): Handles HTTP requests and responses
2. **Service Layer**:
   - `tryOn.py`: Virtual try-on processing
   - `evaluate.py`: Fashion feedback generation
   - `cloudinary_service.py`: Image storage and retrieval
   - `database_service.py`: Database operations
3. **Database Layer**: PostgreSQL with versioned schema
4. **AI Models**:
   - CatVTON: For generating virtual try-on images
   - Google Gemini: For fashion analysis and feedback

## API Endpoints

### Core Endpoints
- `GET /` - Health check endpoint

### Image Upload
- `POST /api/upload/images` - Upload person and/or clothing images
  - Optional: `person_image` (file), `clothing_image` (file), `user_id` (form field)
  - At least one image must be provided
  - Returns image IDs and URLs

### Try-On Processing
- `POST /api/try-on/process` - Process a virtual try-on with previously uploaded images
  - Required: `person_id` (form field), `clothing_id` (form field)
  - Optional: `user_id` (form field)
  - Returns result image URL and related information

### Fashion Feedback
- `POST /api/feedback/{result_id}` - Get AI-powered fashion feedback for a try-on result
  - Returns structured feedback with style recommendations

### History Management
- `GET /api/history/{user_id}` - Get a user's try-on history
- `DELETE /api/history/{result_id}` - Delete a specific try-on result

### Image Retrieval
- `GET /api/user-image/{result_id}?redirect=false` - Get the user/person image URL
- `GET /api/clothing-image/{result_id}?redirect=false` - Get the clothing image URL
- `GET /api/tryon-image/{result_id}?redirect=false` - Get the try-on result image URL
  - Set `redirect=true` to be redirected directly to the image

### Database Info
- `GET /api/database-info` - Get database connection information (masked for security)
- `GET /api/schema-version` - Get the current database schema version

## API Response Format

Most API responses follow this standard format:

```json
{
  "success": true,
  "message": "Optional message explaining the result",
  "data fields": "..." // Endpoint-specific data
}
```

Error responses include:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

## Database Schema

The application uses the following database schema:

### Tables
- `users` - User information
- `users_image` - Person/user images
- `clothes` - Clothing images
- `tryOnImage` - Try-on results linking person and clothing images
- `feedback` - AI-generated fashion feedback for try-on results
- `schema_version` - Tracks database schema versions

## Setup Instructions

### Prerequisites
- Python 3.8+ (3.10 recommended)
- PostgreSQL 13+
- Cloudinary account
- Google Gemini API key (for fashion feedback)
- 8GB+ VRAM (16GB recommended for AI processing)
- 8GB+ RAM
- CUDA-compatible GPU (optional but recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/HackAIthon.git
cd HackAIthon
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```
# PostgreSQL Configuration
POSTGRES_HOST=your_postgres_host
POSTGRES_DB=your_database_name
POSTGRES_USER=your_postgres_username
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_PORT=your_postgres_port

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

4. The database tables will be created automatically on startup. If you need to reset the database, run:
```bash
python API/Database/database_service.py
```

### Running the Application

Start the API server:
```bash
cd API
python main.py
```

The server will start on http://0.0.0.0:8000. Access the Swagger documentation at http://0.0.0.0:8000/docs.

## Usage Examples

### Complete Try-On Workflow

```python
import requests

# 1. Upload images
upload_url = "http://localhost:8000/api/upload/images"
files = {
    'person_image': ('person.jpg', open('path/to/person.jpg', 'rb'), 'image/jpeg'),
    'clothing_image': ('clothing.jpg', open('path/to/clothing.jpg', 'rb'), 'image/jpeg')
}
upload_response = requests.post(upload_url, files=files)
result = upload_response.json()

# Get the image IDs
person_id = result['person_id']
clothing_id = result['clothing_id']

# 2. Process try-on
tryon_url = "http://localhost:8000/api/try-on/process"
data = {
    'person_id': person_id,
    'clothing_id': clothing_id
}
tryon_response = requests.post(tryon_url, data=data)
tryon_result = tryon_response.json()

# Get the result ID
result_id = tryon_result['result_id']
result_url = tryon_result['result_url']

# 3. Get fashion feedback
feedback_url = f"http://localhost:8000/api/feedback/{result_id}"
feedback_response = requests.post(feedback_url)
feedback = feedback_response.json()

print(f"Try-on image: {result_url}")
print("Fashion feedback:", feedback['feedback'])
```

### Using cURL

```bash
# Upload images
curl -X POST "http://localhost:8000/api/upload/images" \
  -F "person_image=@path/to/person.jpg" \
  -F "clothing_image=@path/to/clothing.jpg"

# Process try-on (replace IDs with actual values)
curl -X POST "http://localhost:8000/api/try-on/process" \
  -F "person_id=1" \
  -F "clothing_id=2"

# Get fashion feedback (replace with actual result ID)
curl -X POST "http://localhost:8000/api/feedback/1"
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Check your PostgreSQL connection details in `.env`
   - Ensure PostgreSQL service is running
   - Try running `python API/Database/database_service.py` to verify connection

2. **Image Upload Failures**:
   - Verify Cloudinary credentials
   - Check if image format is supported (JPG, PNG recommended)
   - Ensure image file size is under Cloudinary limits

3. **Try-On Processing Errors**:
   - For CUDA errors, check GPU compatibility and drivers
   - For memory errors, try reducing image dimensions or using a machine with more RAM
   - Verify all model files are downloaded properly

4. **Fashion Feedback Issues**:
   - Check if Gemini API key is valid
   - Ensure internet connectivity for API calls
   - Verify the result image exists

### Logs

Check application logs for detailed error information. Key log messages appear in:

- Standard output during operation
- PostgreSQL logs for database issues
- Cloudinary dashboard for storage issues

## Performance Optimization

For better performance:

1. Use a CUDA-compatible GPU for faster processing
2. Optimize image dimensions before uploading
3. Set up PostgreSQL with proper indexes and configuration
4. Consider using connection pooling for database operations
5. Implement caching for frequently accessed results

## Deployment Considerations

For production deployment:

1. Use a production-ready ASGI server like Uvicorn behind Nginx
2. Set up proper database connection pooling
3. Configure TLS/SSL for secure connections
4. Implement proper authentication and authorization
5. Set up monitoring and logging
6. Consider using Docker for containerization

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
