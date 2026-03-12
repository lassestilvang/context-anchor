import json
import boto3
import os

def test_llama_synthesis():
    model_id = "us.meta.llama3-2-3b-instruct-v1:0"
    region = "us-east-1"
    
    bedrock = boto3.client("bedrock-runtime", region_name=region)
    
    system_prompt = "You are a helpful assistant. Respond in JSON."
    user_message = "Hello, tell me about context management."
    
    prompt_payload = {
        "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        "max_gen_len": 100,
        "temperature": 0.1,
    }
    
    body = json.dumps(prompt_payload)
    
    print(f"Testing model: {model_id}")
    print(f"Body: {body}")
    
    try:
        response = bedrock.invoke_model(modelId=model_id, body=body)
        response_body = json.loads(response.get("body").read())
        print("Success!")
        print(f"Response: {json.dumps(response_body, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_llama_synthesis()
