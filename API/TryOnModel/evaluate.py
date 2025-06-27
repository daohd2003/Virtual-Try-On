import google.generativeai as genai
import PIL.Image
import json

# Configure your API key
genai.configure(api_key="AIzaSyBLFpdCcrg4M67m5kNfT7QxBnFGQT3UAFE")

def get_fashion_feedback(image_path):
    """Generates fashion feedback from Gemini using a virtual try-on image.

    Args:
        image_path: The path to the virtual try-on image.

    Returns:
        dict: A dictionary containing structured fashion feedback
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        img = PIL.Image.open(image_path)

        prompt = """Bạn là một chuyên gia tư vấn thời trang chuyên nghiệp. Hãy cung cấp phản hồi chi tiết và hữu ích về hình ảnh thử đồ ảo này.
        Phân tích kỹ lưỡng độ vừa vặn, sự phối hợp màu sắc và phong cách tổng thể. Đề xuất những cải tiến tiềm năng hoặc các lựa chọn thay thế.
        Hãy đưa ra nhận xét cụ thể, mang tính xây dựng và thể hiện sự tinh tế trong chuyên môn.
        
        Đầu ra PHẢI là một JSON hợp lệ theo định dạng này:
        {
            "feedback": "Nhận xét chi tiết về trang phục",
            "recommendations": ["Đề xuất 1", "Đề xuất 2", "Đề xuất 3"],
            "overall_score": [1 đến 10]
        }
        
        Chỉ trả về JSON, không thêm văn bản nào khác. Đảm bảo JSON hợp lệ và có đầy đủ các trường."""

        response = model.generate_content([prompt, img])
        
        # Attempt to parse JSON from the response
        try:
            # Clean the response text to extract only JSON
            text = response.text.strip()
            
            # If the response is wrapped in markdown code blocks, remove them
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
                if text.endswith("```"):
                    text = text[:-3]
            elif text.startswith("```"):
                text = text.replace("```", "", 1)
                if text.endswith("```"):
                    text = text[:-3]
                    
            # Parse the cleaned text as JSON
            feedback_json = json.loads(text.strip())
            return feedback_json
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return a structured error response with the original text
            print(f"JSON parsing error: {e}")
            print(f"Original response: {response.text}")
            
            return {
                "error": "Failed to parse response as JSON",
                "raw_response": response.text,
                "error_details": str(e)
            }
    
    except Exception as e:
        # Handle any other exceptions
        print(f"Error generating fashion feedback: {e}")
        return {
            "error": "Error generating fashion feedback",
            "details": str(e)
        }


if __name__ == "__main__":
    # Example usage
    # Replace with the path to your image file
    image_path = "D:/Duma Down j lam vay/hackaithon_data-20250309T172519Z-001/hackaithon_data/men.jpg"

    feedback = get_fashion_feedback(image_path)
    print(json.dumps(feedback, ensure_ascii=False, indent=2))