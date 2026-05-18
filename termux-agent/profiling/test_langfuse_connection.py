import os
from langfuse import Langfuse

# Force set the keys
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-afa343c3-b7e1-4dc1-bac9-ff3a1daa9159"
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-6228d3f8-4b84-486c-b0ad-a8292b25b307"
os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com"

print("Initializing Langfuse client...")
try:
    langfuse = Langfuse()
    
    print("Creating a test trace...")
    trace = langfuse.trace(
        name="hello-world-test",
        user_id="user-1234",
        metadata={"test": "true"}
    )
    
    print("Adding a span...")
    span = trace.span(
        name="test-span",
        input={"prompt": "test message"}
    )
    
    span.end(output={"response": "success"})
    
    print("Flushing data...")
    langfuse.flush()
    print("Done! Data flushed.")
except Exception as e:
    print(f"Error occurred: {e}")
