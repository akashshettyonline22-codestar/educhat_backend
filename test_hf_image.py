import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_new_huggingface_api():
    """Test NEW Hugging Face API endpoint"""
    
    hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
    print(f"Token found: {hf_token[:10]}..." if hf_token else "No token found!")
    
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    
    # Try NEW API first
    API_URL_NEW = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    
    payload = {
        "inputs": "A colorful cartoon apple for children, simple illustration, bright colors, educational",
        "parameters": {
            "num_inference_steps": 4,
            "guidance_scale": 1.0,
            "width": 1024,
            "height": 1024
        }
    }
    
    print("Testing NEW HuggingFace API...")
    response = requests.post(API_URL_NEW, headers=headers, json=payload, timeout=60)
    
    print(f"NEW API Status: {response.status_code}")
    
    if response.status_code == 200:
        with open("test_image_new.png", "wb") as f:
            f.write(response.content)
        print("✅ NEW API SUCCESS! Image saved as test_image_new.png")
        return True
    else:
        print(f"NEW API Error: {response.text}")
        
        # Try fallback
        print("\nTrying fallback API...")
        API_URL_OLD = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        
        payload_old = {
            "inputs": "A colorful cartoon apple for children, simple illustration, bright colors",
            "parameters": {
                "num_inference_steps": 20,
                "guidance_scale": 7.0
            }
        }
        
        response_old = requests.post(API_URL_OLD, headers=headers, json=payload_old, timeout=30)
        
        print(f"Fallback API Status: {response_old.status_code}")
        
        if response_old.status_code == 200:
            with open("test_image_fallback.png", "wb") as f:
                f.write(response_old.content)
            print("✅ FALLBACK SUCCESS! Image saved as test_image_fallback.png")
            return True
        else:
            print(f"❌ Both APIs failed: {response_old.text}")
            return False

if __name__ == "__main__":
    test_new_huggingface_api()
