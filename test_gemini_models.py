#!/usr/bin/env python3
"""
Test script to find the correct Gemini model for audio support
"""

import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

def test_models():
    """Test which models are available and support audio."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return
    
    genai.configure(api_key=api_key)
    
    print("🔍 Listing all available Gemini models...\n")
    print("="*80)
    
    for model in genai.list_models():
        print(f"\nModel: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Supported methods: {model.supported_generation_methods}")
        print(f"  Input token limit: {model.input_token_limit}")
        print(f"  Output token limit: {model.output_token_limit}")
    
    print("\n" + "="*80)
    print("\n✅ Testing which models work for generateContent with audio...\n")
    
    # Test models that might work
    test_models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-latest",
    ]
    
    for model_name in test_models:
        try:
            model = genai.GenerativeModel(model_name)
            # Try a simple text generation first
            response = model.generate_content("Say 'test successful'")
            print(f"✅ {model_name} - WORKS for text generation")
        except Exception as e:
            print(f"❌ {model_name} - FAILED: {str(e)[:100]}")

if __name__ == "__main__":
    test_models()
