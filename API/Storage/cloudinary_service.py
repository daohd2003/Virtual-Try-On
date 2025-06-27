import cloudinary
import os
import cloudinary.uploader as uploader
import cloudinary.api
import dotenv
import requests

dotenv.load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

def upload_image(image_path: str, preserve_filename: bool = False):
    """
    Upload an image to Cloudinary
    
    Args:
        image_path (str): Path to the image file
        preserve_filename (bool): If True, preserves the original filename. If False, Cloudinary generates a unique name.
        
    Returns:
        str: The secure URL of the uploaded image
    """
    if os.path.exists(image_path):
        print(f"Uploading image: {image_path}")
        
        # Get the original filename without extension
        original_filename = os.path.splitext(os.path.basename(image_path))[0]
        
        # Configure upload options
        upload_options = {
            "folder": "HackAIThon",
            "use_filename": preserve_filename,
            "unique_filename": not preserve_filename
        }
        
        if preserve_filename:
            upload_options["public_id"] = original_filename
            
        result = uploader.upload(image_path, **upload_options)
        print(f"Upload successful! Image URL: {result['secure_url']}")
        
    else:
        print(f"File does not exist: {image_path}")
        return None

    return result["secure_url"]

def delete_image(public_id: str):
    """
    Delete an image from Cloudinary using its public_id if it exists
    
    Args:
        public_id (str): The public_id of the image to delete
        
    Returns:
        dict: The result of the deletion operation if successful, None if image doesn't exist or deletion fails
    """
    try:
        # Check if the image exists
        try:
            cloudinary.api.resource(public_id)
        except Exception as e:
            print(f"Image with public_id '{public_id}' does not exist in Cloudinary")
            return None
            
        # If we get here, the image exists, so delete it
        result = uploader.destroy(public_id)
        print(f"Successfully deleted image with public_id: {public_id}")
        return result
    except Exception as e:
        print(f"Error deleting image: {str(e)}")
        return None
    
def retrive_image_from_url(image_url: str):
    response = requests.get(image_url)
    return response.content

def save_image(image_url: str, image_name: str):
    image = retrive_image_from_url(image_url)
    with open(image_name, "wb") as f:
        f.write(image)

if __name__ == "__main__":
    # Example with original filename preserved
    # upload_image("E:/RhythmGC_Code/HackAIthon/API/TryOnModel/Image/output/20250316230501.png", preserve_filename=True)
    # Example with Cloudinary-generated filename
    # upload_image("E:/RhythmGC_Code/HackAIthon/API/TryOnModel/Image/output/20250316230501.png", preserve_filename=False)
    delete_image("HackAIThon/20250316230501")  # Example public_id
