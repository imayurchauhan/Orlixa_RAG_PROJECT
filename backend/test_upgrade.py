import os
import shutil
import uuid
import asyncio
from app.rag import index_document
from app.router import route_query
from app.config import VECTOR_DIR

async def run_tests():
    print("--- TEST 1: Document Upload & Query ---")
    session_id_1 = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    
    # Create a dummy doc
    dummy_doc = "test_doc.txt"
    with open(dummy_doc, "w") as f:
        f.write("The secret code to the mainframe is X99-Omega.")
    
    # Upload & Index
    os.makedirs(VECTOR_DIR / session_id_1, exist_ok=True)
    dest = VECTOR_DIR / session_id_1 / dummy_doc
    shutil.copy(dummy_doc, dest)
    
    print("Indexing document...")
    # Using run_in_executor
    await loop.run_in_executor(None, index_document, session_id_1, str(dest))
    
    print("Querying Document...")
    res1 = await loop.run_in_executor(None, route_query, session_id_1, "What is the secret code?")
    print(f"Result 1 [{res1['source']}]: {res1['answer']}\n")
    assert res1['source'] == "document"
    
    print("--- TEST 2: New Chat Isolation ---")
    session_id_2 = uuid.uuid4().hex
    print("Querying New Chat...")
    res2 = await loop.run_in_executor(None, route_query, session_id_2, "What is the secret code?")
    print(f"Result 2 [{res2['source']}]: {res2['answer']}\n")
    assert res2['source'] != "document"
    
    print("--- TEST 3: Web Search Trigger ---")
    res3 = await loop.run_in_executor(None, route_query, session_id_2, "What IPL match today?")
    print(f"Result 3 [{res3['source']}]: {res3['answer']}\n")
    assert res3['source'] == "web"
    
    print("--- TEST 4: History Persistence ---")
    # Query with session_id_2 again to test history
    res4 = await loop.run_in_executor(None, route_query, session_id_2, "What did I just ask you about?")
    print(f"Result 4 [{res4['source']}]: {res4['answer']}\n")
    
    print("ALL TESTS PASSED!")
    os.remove(dummy_doc)

if __name__ == "__main__":
    asyncio.run(run_tests())
