import os
import sys
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", message="You are using `torch.load` with `weights_only=False`")

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
# Add local CatVTON directories to python path
catVTON_dir = os.path.join(os.path.dirname(__file__), 'CatVTON')
sys.path.append(catVTON_dir)

from datetime import datetime
import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image
from API.TryOnModel.CatVTON.model.cloth_masker import AutoMasker, vis_mask
from API.TryOnModel.CatVTON.model.pipeline import CatVTONPipeline
from API.TryOnModel.CatVTON.utils import init_weight_dtype, resize_and_crop, resize_and_padding
import matplotlib.pyplot as plt
print("Imported tryOnModel modules successfully")

# Set custom model download directory
custom_model_dir = os.path.join(os.path.dirname(__file__), 'Model')
os.makedirs(custom_model_dir, exist_ok=True)

# Check if model already exists
if os.path.exists(os.path.join(custom_model_dir, 'DensePose')) and os.path.exists(os.path.join(custom_model_dir, 'SCHP')):
    print(f"Model already exists at {custom_model_dir}, skipping download")
    repo_path = custom_model_dir
else:
    print(f"Downloading model to {custom_model_dir}...")
    repo_path = snapshot_download(repo_id="zhengchong/CatVTON", local_dir=custom_model_dir)
    print(f"Model downloaded to {repo_path}")

# Check if CUDA is available
if torch.cuda.is_available():
    device = 'cuda'
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    device = 'cpu'
    print("CUDA not available, using CPU instead")

# Add friendly message about the warning
print("Note: Some model loading warnings may appear. These are expected and don't affect functionality.")

pipeline = CatVTONPipeline(
    base_ckpt="booksforcharlie/stable-diffusion-inpainting",
    attn_ckpt=repo_path,
    attn_ckpt_version="mix",
    weight_dtype=init_weight_dtype("fp16"),
    use_tf32=True,
    device=device
)

mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device=device,
)

seed = 42
width = 768
height = 1024
cloth_type = 'upper'
num_inference_steps = 50
guidance_scale = 3.5

def infer_single_image(person_image, cloth_image, cloth_type='upper'):
    # Use absolute paths for output
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "Image", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d%H%M%S")
    result_save_path = os.path.join(output_dir, f"{date_str}.png")

    generator = None
    if seed != -1:
        generator = torch.Generator(device=device).manual_seed(seed)

    print(f"Loading images from:\n- Person: {person_image}\n- Cloth: {cloth_image}")
    person_image = Image.open(person_image).convert("RGB")
    cloth_image = Image.open(cloth_image).convert("RGB")
    person_image = resize_and_crop(person_image, (width, height))
    cloth_image = resize_and_padding(cloth_image, (width, height))
    print("Images loaded and resized successfully")
    print(f"[DEBUG] infer_single_image() called with cloth_type = {cloth_type}")

    print("Generating mask...")
    mask = automasker(person_image, cloth_type)['mask']
    mask = mask_processor.blur(mask, blur_factor=9)
    print("Mask generated")

    print(f"Running inference with {num_inference_steps} steps...")
    result_image = pipeline(
        image=person_image,
        condition_image=cloth_image,
        mask=mask,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=generator
    )[0]
    print("Inference complete")
    
    result_image.save(result_save_path)
    print(f"Result saved at: {result_save_path}")
    return result_save_path

if __name__ == "__main__":
    # Use absolute paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create directories
    input_user_dir = os.path.join(current_dir, "Image", "input", "user")
    input_clothes_dir = os.path.join(current_dir, "Image", "input", "clothes")
    os.makedirs(input_user_dir, exist_ok=True)
    os.makedirs(input_clothes_dir, exist_ok=True)
    
    # Sample image paths
    input_img_people = os.path.join(input_user_dir, "3a60d42f-bb12-433f-9391-bde8816c31b8.jpg")
    input_img_clothes = os.path.join(input_clothes_dir, "5d293d04-eb8c-4a38-a5d7-3ca7a6aacca3.jpg")
    
    # Check for sample images
    if not os.path.exists(input_img_people) or not os.path.exists(input_img_clothes):
        print(f"Warning: Input images not found at {input_img_people} or {input_img_clothes}")
        print("Please place your input images in the correct directories before running")
        
        # Print directories where images should be placed
        print(f"Place person image in: {input_user_dir}")
        print(f"Place clothes image in: {input_clothes_dir}")
    else:
        output_path = infer_single_image(input_img_people, input_img_clothes)
        print(f"Virtual try-on completed successfully! Output saved to: {output_path}")