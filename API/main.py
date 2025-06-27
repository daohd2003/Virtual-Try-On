from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import uuid
import shutil
from datetime import datetime
from typing import Optional
import time
import json
import pyodbc

# Import our services
from TryOnModel.tryOn import infer_single_image
from Database.database_service import insert_data, update_data, execute_query, delete_data, getConnectionString, create_tables, get_connection
from Storage.cloudinary_service import upload_image, delete_image, retrive_image_from_url, save_image
from TryOnModel.evaluate import get_fashion_feedback

# Create the FastAPI app
app = FastAPI(
    title="Virtual Try-On API",
    description="API for virtual clothing try-on service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Expose all headers
)

# Temporary file storage
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and check schema version on application startup"""
    # Create tables if they don't exist
    create_tables()

    # Check schema version
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Thay thế LIMIT 1 bằng TOP 1
                cur.execute("SELECT TOP 1 version_number FROM schema_version ORDER BY applied_date DESC")
                result = cur.fetchone()
                if result:
                    version = result[0]
                    print(f"Database schema version: {version}")
                else:
                    print("Warning: No schema version found in database")
        except Exception as e:
            print(f"Error checking schema version: {str(e)}")
        finally:
            conn.close()

    print("Database tables initialized")

def save_uploaded_file(upload_file: UploadFile) -> str:
    """Save an uploaded file to disk and return the path"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{uuid.uuid4().hex}{os.path.splitext(upload_file.filename)[1]}"
    file_path = os.path.join(TEMP_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path

def cleanup_temp_files(file_paths):
    """Delete temporary files after processing"""
    for path in file_paths:
        if os.path.exists(path):
            os.remove(path)
            print(f"Deleted temp file: {path}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "online", "message": "Virtual Try-On API is running"}

@app.post("/api/upload/images")
async def upload_images(
    background_tasks: BackgroundTasks,
    person_image: Optional[UploadFile] = File(None),
    clothing_image: Optional[UploadFile] = File(None),
    user_id: Optional[int] = Form(None)
):
    """
    Upload person and/or clothing images for virtual try-on
    
    - **person_image**: Optional image of the person
    - **clothing_image**: Optional image of the clothing item
    - **user_id**: Optional user ID to associate with the images
    
    At least one image must be provided.
    """
    if not person_image and not clothing_image:
        raise HTTPException(status_code=400, detail="At least one image must be provided")
    
    conn = None
    temp_files = []
    result = {"success": True}
    
    try:
        # Get database connection
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Validate user_id if provided
        effective_user_id = None
        if user_id and user_id > 0:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                user_exists = cur.fetchone()
                if user_exists:
                    effective_user_id = user_id
                else:
                    print(f"Warning: User ID {user_id} not found in database, images will be uploaded without user association")
        
        with conn.cursor() as cur:
            # Process person image if provided
            if person_image:
                # Save uploaded file temporarily
                person_path = save_uploaded_file(person_image)
                temp_files.append(person_path)
                
                # Upload to cloudinary
                person_url = upload_image(person_path, preserve_filename=True)
                
                # Extract public_id from URL
                person_public_id = person_url.split("/")[-1].split(".")[0]
                
                # Store person image in database (new schema)
                cur.execute("""
                    INSERT INTO users_image (user_id, public_id, url, upload_date)
                    VALUES (?, ?, ?, ?);
                    SELECT SCOPE_IDENTITY();
                """, (effective_user_id, person_public_id, person_url, datetime.now()))
                cur.nextset()
                person_id = cur.fetchone()[0]
                
                # Add to result
                result["person_id"] = person_id
                result["person_url"] = person_url
                result["person_public_id"] = person_public_id
            
            # Process clothing image if provided
            if clothing_image:
                # Save uploaded file temporarily
                clothing_path = save_uploaded_file(clothing_image)
                temp_files.append(clothing_path)
                
                # Upload to cloudinary
                clothing_url = upload_image(clothing_path, preserve_filename=True)
                
                # Extract public_id from URL
                clothing_public_id = clothing_url.split("/")[-1].split(".")[0]
                
                # Store clothing image in database (new schema)
                cur.execute("""
                    INSERT INTO clothes (user_id, public_id, url, upload_date)
                    VALUES (?, ?, ?, ?);
                    SELECT SCOPE_IDENTITY();
                """, (effective_user_id, clothing_public_id, clothing_url, datetime.now()))
                cur.nextset()
                clothing_id = cur.fetchone()[0]
                
                # Add to result
                result["clothing_id"] = clothing_id
                result["clothing_url"] = clothing_url
                result["clothing_public_id"] = clothing_public_id
            
            # Commit the transaction
            conn.commit()
        
        # Schedule cleanup of temporary files
        background_tasks.add_task(cleanup_temp_files, temp_files)
        
        return result
    except Exception as e:
        # Rollback the transaction in case of error
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading images: {str(e)}")
    finally:
        # Always close the connection
        if conn:
            conn.close()

@app.post("/api/try-on/process")
async def process_try_on(
    background_tasks: BackgroundTasks,
    person_id: int = Form(...),
    clothing_id: int = Form(...),
    user_id: Optional[int] = Form(None)
):
    """
    Process a virtual try-on with previously uploaded images
    
    - **person_id**: ID of the person image in the database
    - **clothing_id**: ID of the clothing image in the database
    - **user_id**: Optional user ID for saving the result to their history
    """
    conn = None
    temp_files = []
    
    try:
        # Get database connection
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Validate user_id if provided
        effective_user_id = None
        if user_id and user_id > 0:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                user_exists = cur.fetchone()
                if user_exists:
                    effective_user_id = user_id
                else:
                    print(f"Warning: User ID {user_id} not found in database, result will be saved without user association")
        
        with conn.cursor() as cur:
            # Get person image data (from users_image table)
            cur.execute("SELECT * FROM users_image WHERE id = ?", (person_id,))
            person_result = cur.fetchone()
            
            if not person_result:
                raise HTTPException(status_code=404, detail="Person image not found")
            
            # Get clothing image data (from clothes table)
            cur.execute("SELECT * FROM clothes WHERE id = ?", (clothing_id,))
            clothing_result = cur.fetchone()
            
            if not clothing_result:
                raise HTTPException(status_code=404, detail="Clothing image not found")
            
            # Extract URLs from the results
            # We need to access by index based on the column order in the SELECT * query
            person_url = person_result[3]  # Assuming 'url' is the 4th column (0-indexed)
            clothing_url = clothing_result[3]  # Assuming 'url' is the 4th column (0-indexed)
            
            # If user_id not provided, try to get from person image
            if not effective_user_id and person_result[1]:  # person_result[1] should be user_id
                effective_user_id = person_result[1]
            
            # Download images from Cloudinary using the service functions
            person_path = os.path.join(TEMP_DIR, f"person_{uuid.uuid4().hex}.jpg")
            clothing_path = os.path.join(TEMP_DIR, f"clothing_{uuid.uuid4().hex}.jpg")
            
            # Use the save_image function from cloudinary_service
            save_image(person_url, person_path)
            save_image(clothing_url, clothing_path)
            
            temp_files.extend([person_path, clothing_path])
            
            # Process the try-on
            result_path = infer_single_image(person_path, clothing_path)
            temp_files.append(result_path)
            
            # Upload result to cloudinary
            result_url = upload_image(result_path, preserve_filename=True)
            result_public_id = result_url.split("/")[-1].split(".")[0]
            
            # Store result image in database (new schema)
            cur.execute("""
                INSERT INTO tryOnImage (user_id, user_image_id, clothes_id, public_id, url, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                SELECT SCOPE_IDENTITY();
            """, (effective_user_id, person_id, clothing_id, result_public_id, result_url, datetime.now()))
            cur.nextset()
            result_id = cur.fetchone()[0]
            
            # Commit the transaction
            conn.commit()
        
        # Schedule cleanup of temporary files
        background_tasks.add_task(cleanup_temp_files, temp_files)
        
        return {
            "success": True,
            "result_id": result_id,
            "result_url": result_url,
            "person_url": person_url,
            "clothing_url": clothing_url,
            "person_id": person_id,
            "clothing_id": clothing_id,
            "user_id": effective_user_id
        }
    except Exception as e:
        # Rollback the transaction in case of error
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing try-on: {str(e)}")
    finally:
        # Always close the connection
        if conn:
            conn.close()

@app.get("/api/history/{user_id}")
async def get_history(user_id: int):
    """Get try-on history for a user"""
    query = """
    SELECT 
        t.id as result_id,
        t.url as result_url,
        u.url as person_url,
        c.url as clothing_url,
        t.created_at,
        u.id as person_id,
        c.id as clothing_id
    FROM tryOnImage t
    JOIN users_image u ON t.user_image_id = u.id
    JOIN clothes c ON t.clothes_id = c.id
    WHERE t.user_id = %(user_id)s
    ORDER BY t.created_at DESC
    """
    results = execute_query(query, {"user_id": user_id})
    
    if results:
        return {"results": results}
    return {"results": []}

@app.delete("/api/history/{result_id}")
async def delete_history(result_id: int):
    """Delete a try-on result from history"""
    # Get the result URL first to delete from cloudinary
    query = "SELECT public_id, url FROM tryOnImage WHERE id = %(id)s"
    result = execute_query(query, {"id": result_id})
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Extract public_id from the result
    public_id = result[0]["public_id"]
    
    # Delete from cloudinary if public_id exists
    if public_id:
        delete_image(public_id)
    
    # Delete from database
    success = delete_data("tryOnImage", f"id = {result_id}")
    
    if success:
        return {"success": True, "message": "Result deleted successfully"}
    raise HTTPException(status_code=500, detail="Failed to delete result")

@app.get("/api/user-image/{result_id}")
async def get_user_image(result_id: int, redirect: bool = False):
    """
    Get the user/person image for a specific try-on result
    
    - **result_id**: ID of the try-on result
    - **redirect**: If true, redirects to the image instead of returning the URL
    """
    query = """
    SELECT u.url 
    FROM tryOnImage t
    JOIN users_image u ON t.user_image_id = u.id
    WHERE t.id = %(id)s
    """
    result = execute_query(query, {"id": result_id})
    
    if not result or not result[0]["url"]:
        raise HTTPException(status_code=404, detail="User image not found")
    
    image_url = result[0]["url"]
    
    if redirect:
        return RedirectResponse(url=image_url)
    return {"url": image_url}

@app.get("/api/clothing-image/{result_id}")
async def get_clothing_image(result_id: int, redirect: bool = False):
    """
    Get the clothing image for a specific try-on result
    
    - **result_id**: ID of the try-on result
    - **redirect**: If true, redirects to the image instead of returning the URL
    """
    query = """
    SELECT c.url 
    FROM tryOnImage t
    JOIN clothes c ON t.clothes_id = c.id
    WHERE t.id = %(id)s
    """
    result = execute_query(query, {"id": result_id})
    
    if not result or not result[0]["url"]:
        raise HTTPException(status_code=404, detail="Clothing image not found")
    
    image_url = result[0]["url"]
    
    if redirect:
        return RedirectResponse(url=image_url)
    return {"url": image_url}

@app.get("/api/tryon-image/{result_id}")
async def get_tryon_image(result_id: int, redirect: bool = False):
    """
    Get the try-on result image
    
    - **result_id**: ID of the try-on result
    - **redirect**: If true, redirects to the image instead of returning the URL
    """
    query = "SELECT url FROM tryOnImage WHERE id = %(id)s"
    result = execute_query(query, {"id": result_id})
    
    if not result or not result[0]["url"]:
        raise HTTPException(status_code=404, detail="Try-on image not found")
    
    image_url = result[0]["url"]
    
    if redirect:
        return RedirectResponse(url=image_url)
    return {"url": image_url}

# @app.get("/api/database-info")
# async def database_info():
#     """Get database connection information"""
#     try:
#         connection_string = getConnectionString()
#         # Mask the password in the connection string for security
#         masked_connection = connection_string.replace("://", "://******@", 1).split("@", 1)[1]
#         masked_connection = f"postgresql://username:password@{masked_connection}"
#         return {
#             "success": True,
#             "connection_string": masked_connection,
#             "note": "Password has been masked for security reasons"
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error getting database info: {str(e)}")

# --- Endpoint FastAPI đã được sửa đổi để sử dụng logic SQL Server ---

# --- Hàm hỗ trợ che mật khẩu chuỗi kết nối SQL Server ---
def getMaskedConnectionString():
    """
    Get the SQL Server connection string with the password masked.

    Returns:
        dict: A dictionary containing success status, masked connection string, and a note.
    """
    connection_string = getConnectionString()

    # Split the connection string by 'PWD=' to find the password part
    parts = connection_string.split("PWD=")
    if len(parts) > 1:
        # The first part is everything before PWD=
        prefix = parts[0] + "PWD="
        # The second part contains the password and possibly trailing semicolons/options
        password_and_rest = parts[1]

        # Find the end of the password (usually a semicolon or end of string)
        password_end_index = password_and_rest.find(';')
        if password_end_index != -1:
            # If a semicolon is found, extract the password and the rest
            password = password_and_rest[:password_end_index]
            rest_of_string = password_and_rest[password_end_index:]
        else:
            # If no semicolon, the password is the rest of the string
            password = password_and_rest
            rest_of_string = ""

        # Mask the password
        masked_password = "*" * len(password) # Or a fixed number of asterisks like "******"

        # Reconstruct the masked connection string
        masked_connection = f"{prefix}{masked_password}{rest_of_string}"
    else:
        # If 'PWD=' is not found, return the original string (or handle as an error)
        masked_connection = connection_string

    return {
        "success": True,
        "connection_string": masked_connection,
        "note": "Password has been masked for security reasons"
    }

@app.get("/api/database-info")
async def database_info():
    """
    Get database connection information for SQL Server.
    The password in the connection string will be masked for security.
    """
    try:
        # GỌI ĐÚNG HÀM getMaskedConnectionString() để có chuỗi đã che mật khẩu và định dạng trả về đúng
        result = getMaskedConnectionString()

        # Trả về kết quả đã có sẵn success, connection_string và note
        return result
    except Exception as e:
        # Xử lý ngoại lệ và trả về lỗi HTTP 500
        raise HTTPException(status_code=500, detail=f"Error getting database info: {str(e)}")

@app.get("/api/feedback/{result_id}")
async def retrieve_or_generate_feedback(
    result_id: int,
    background_tasks: BackgroundTasks
):
    """
    Retrieve saved fashion feedback for a try-on result or generate new feedback if none exists
    
    - **result_id**: ID of the try-on result
    
    Returns the feedback, either existing or newly generated
    """
    # First check if feedback already exists
    query = """
    SELECT f.id as feedback_id, f.feedback, f.created_at, t.url as result_image_url
    FROM feedback f
    JOIN tryOnImage t ON f.tryOnImage_id = t.id
    WHERE f.tryOnImage_id = %(result_id)s
    ORDER BY f.created_at DESC
    LIMIT 1
    """
    
    result = execute_query(query, {"result_id": result_id})
    
    # If feedback exists, return it
    if result:
        feedback_data = result[0]
        
        # Parse the feedback if it's stored as a JSON string
        feedback_content = feedback_data["feedback"]
        if isinstance(feedback_content, str):
            try:
                feedback_content = json.loads(feedback_content)
            except json.JSONDecodeError:
                # If it's not valid JSON, keep it as is
                pass
        
        # Format the feedback for UI display
        formatted_text = format_feedback_for_ui(feedback_content)
        
        # Return the feedback
        return {
            "status": "success",
            "message": "Feedback retrieved successfully",
            "data": {
                "feedback": feedback_content,
                "formatted_text": formatted_text
            }
        }
    
    # If no feedback exists, generate new feedback
    # For GET requests, we'll forward to generate feedback
    return await generate_new_feedback(result_id, background_tasks)

@app.post("/api/feedback/{result_id}")
async def generate_new_feedback(
    result_id: int,
    background_tasks: BackgroundTasks
):
    """
    Generate new fashion feedback for a try-on result, even if feedback already exists
    
    - **result_id**: ID of the try-on result
    
    Returns newly generated feedback
    """
    # Get the result image URL from tryOnImage table
    query = "SELECT url, id FROM tryOnImage WHERE id = %(result_id)s"
    result = execute_query(query, {"result_id": result_id})
    
    if not result or not result[0]["url"]:
        raise HTTPException(status_code=404, detail="Try-on result not found")
    
    result_url = result[0]["url"]
    temp_files = []
    
    try:
        # Download the image
        result_path = os.path.join(TEMP_DIR, f"result_{uuid.uuid4().hex}.jpg")
        save_image(result_url, result_path)
        temp_files.append(result_path)
        
        # Generate fashion feedback
        feedback = get_fashion_feedback(result_path)
        
        # Store feedback in database
        feedback_id = None
        try:
            feedback_data = {
                "tryOnImage_id": result_id,
                "feedback": feedback if isinstance(feedback, str) else json.dumps(feedback)
            }
            feedback_id = insert_data("feedback", feedback_data)
        except Exception as e:
            print(f"Error storing feedback: {str(e)}")
        
        # Format the feedback for UI display
        formatted_text = format_feedback_for_ui(feedback)
        
        # Schedule cleanup of temporary files
        background_tasks.add_task(cleanup_temp_files, temp_files)
        
        # Return the feedback
        return {
            "status": "success",
            "message": "Feedback generated successfully",
            "data": {
                "feedback": feedback,
                "formatted_text": formatted_text
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating fashion feedback: {str(e)}")
    finally:
        # Clean up temp files immediately if there was an error
        for path in temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

def format_feedback_for_ui(feedback):
    """
    Format feedback object into readable text for UI display
    
    Args:
        feedback: The feedback object or string
        
    Returns:
        str: Formatted text ready for UI display
    """
    if isinstance(feedback, str):
        try:
            feedback = json.loads(feedback)
        except json.JSONDecodeError:
            return feedback
    
    formatted_sections = []
    
    # Format feedback text section
    if feedback.get("feedback"):
        feedback_section = []
        feedback_section.append("💬 NHẬN XÉT CHI TIẾT:")
        feedback_section.append(feedback["feedback"])
        formatted_sections.append("\n".join(feedback_section))
    
    # Format recommendations section
    if feedback.get("recommendations") and isinstance(feedback["recommendations"], list):
        recommendations_section = []
        recommendations_section.append("✨ ĐỀ XUẤT:")
        for i, recommendation in enumerate(feedback["recommendations"], 1):
            recommendations_section.append(f"▶️ {i}. {recommendation}")
        formatted_sections.append("\n".join(recommendations_section))
    
    # Format overall score section
    if feedback.get("overall_score") is not None:
        score_section = []
        score_section.append("💯 ĐIỂM ĐÁNH GIÁ TỔNG THỂ:")
        score = feedback["overall_score"]
        # Convert score to string with visual representation
        if isinstance(score, (int, float)):
            stars = "★" * int(min(score, 10))
            empty_stars = "☆" * (10 - int(min(score, 10)))
            score_section.append(f"{stars}{empty_stars} ({score}/10)")
        else:
            score_section.append(str(score))
        formatted_sections.append("\n".join(score_section))
    
    # If we have no structured content, return the raw JSON
    if not formatted_sections:
        return json.dumps(feedback, ensure_ascii=False, indent=2)
    
    # Join all sections with double newlines
    return "\n\n".join(formatted_sections)

@app.get("/api/schema-version")
async def get_schema_version():
    """Get the current database schema version"""
    try:
        conn = get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT TOP 1 version_number, applied_date 
                FROM schema_version 
                ORDER BY applied_date DESC 
            """)
            result = cur.fetchone()
            
            if result:
                return {
                    "success": True,
                    "version": result[0],
                    "applied_at": result[1]
                }
            else:
                return {
                    "success": False,
                    "message": "No schema version found"
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schema version: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)