# features/myra.py
import base64
import tempfile
import uuid

import filetype
import numpy as np
import requests
from PyPDF2 import PdfReader
from pymongo import MongoClient

from redis_client import get_redis
from config import client, MONGO_URI, TELEGRAM_TOKEN, TELEGRAM_API_URL
from telegram_api import send_message

# TEMP: Mongo cluster unreachable for local testing — commented out.
# Uncomment once MONGO_URI points to a reachable Atlas cluster.
# mongo_client = MongoClient(MONGO_URI)
# collection = mongo_client["myra_training"]["embeddings"]


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


def get_top_k_chunks(query, k=3):
    # Embed the user query
    embedding = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    ).data[0].embedding

    # Get all embeddings from MongoDB
    all_docs = list(collection.find({}))
    scored = []

    for doc in all_docs:
        score = cosine_similarity(embedding, doc["embedding"])
        scored.append((score, doc["chunk"]))

    # Sort by similarity (descending) and take top-k
    scored.sort(reverse=True, key=lambda x: x[0])
    top_chunks = [chunk for _, chunk in scored[:k]]

    return top_chunks


def cmd_askmyra(chat_id, args, user_id, user_name):
    prompt = " ".join(args)
    if len(prompt) == 0:
        send_message(chat_id, "Eh? What do you want to ask? Don't waste my time. -MG Myra")
        return
    elif len(prompt) >= 250:
        send_message(chat_id, "Oi. Yappa yappa yappa. Don't waste my time. Can TLDR or not. -MG Myra")
        return
    else:
        context_chunks = get_top_k_chunks(prompt, k=3)
        context_block = "\n\n---\n\n".join(context_chunks)
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": f'''You are MG Myra — a 22-year-old Singaporean Chinese student at NUS majoring in Environmental Engineering, but really the Head RA at RC4 who runs everything like it’s your empire.

Rules:
- If the user asks a **serious/proper question** (e.g., duty info, real help), give a **short, clear, no-fluff answer**:
  - Use bullet points if multiple points.
  - Include steps if needed.
  - Keep it professional and concise, not sassy.
- If the user asks a **troll/silly question**, then:
  - Optional Roast + Sarcasm (short, witty).
  - Real answer (still correct, but compact).
  - Bonus: Creative insult if the question deserves it.

Keep answers short and sweet. Do not add unnecessary personality when the user genuinely needs help.

--- CONTEXT START ---
{context_block}
--- CONTEXT END ---
'''
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )
        print(response.choices[0].message.content)
        send_message(chat_id, response.choices[0].message.content)
        return


def cmd_trainmyra(chat_id, args, user_id, user_name):
    r = get_redis()
    if not args:
        r.hset("waiting_for_training_file", str(user_id), "true")
        send_message(chat_id, "📥 Please send a file or photo to train Myra.")
    else:
        handle_training_text(chat_id, " ".join(args), user_id, user_name)
        send_message(chat_id, "✅ Trained Myra with text.")
        return


def extract_text_from_image_with_gpt(file_data):
    image_base64 = base64.b64encode(file_data).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please extract all readable text from this image."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content.strip()


def handle_training_file(chat_id, file_id, file_name, user_id, user_name):
    try:
        file_info = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        file_data = requests.get(file_url).content

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(file_data)
            tmp_path = tmp_file.name

        # Extract text
        kind = filetype.guess(file_data)
        extracted_text = ""

        if file_name.endswith(".pdf"):
            reader = PdfReader(tmp_path)
            extracted_text = "\n".join([page.extract_text() or "" for page in reader.pages])
            split_by_paragraphs = True

        elif kind and kind.mime.startswith("image/"):
            extracted_text = extract_text_from_image_with_gpt(file_data)
            split_by_paragraphs = False  # Keep as one chunk

        else:
            extracted_text = file_data.decode("utf-8", errors="ignore")
            split_by_paragraphs = True

        # Clean + chunk text
        chunks = []
        if split_by_paragraphs:
            paragraphs = [p.strip() for p in extracted_text.split("\n\n") if len(p.strip()) > 10]
            for p in paragraphs:
                if len(p) > 5000:
                    chunks += [p[i:i+5000] for i in range(0, len(p), 3000)]
                else:
                    chunks.append(p)
        else:
            cleaned = extracted_text.strip()
            if len(cleaned) > 0:
                chunks.append(cleaned)

        # Embed + insert into Mongo
        for chunk in chunks:
            embedding = client.embeddings.create(
                input=chunk,
                model="text-embedding-3-small"
            ).data[0].embedding

            doc = {
                "_id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "user_name": user_name,
                "file_name": file_name,
                "chunk": chunk,
                "embedding": embedding,
            }
            collection.insert_one(doc)

        send_message(chat_id, f"✅ Trained Myra with `{file_name}` ({len(chunks)} chunks).")

    except Exception as e:
        send_message(chat_id, f"❌ Failed to train Myra: {str(e)}")


def handle_training_text(chat_id, text, user_id, user_name):
    try:
        embedding = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        ).data[0].embedding

        doc = {
            "_id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "user_name": user_name,
            "file_name": "Text",
            "chunk": text,
            "embedding": embedding,
        }
        collection.insert_one(doc)

    except Exception as e:
        send_message(chat_id, f"❌ Failed to train Myra: {str(e)}")


def try_handle_upload(chat_id, message, user_id, user_name):
    """If this user is expected to send a training file/photo, consume the message and handle it."""
    r = get_redis()
    is_waiting = r.hget("waiting_for_training_file", str(user_id)) == "true"
    print(is_waiting)

    if not is_waiting:
        return False

    file_id = None
    file_name = None

    if "document" in message:
        file_id = message["document"]["file_id"]
        file_name = message["document"].get("file_name", "unknown_file")

    elif "photo" in message:
        photo = message["photo"][-1]  # largest version
        file_id = photo["file_id"]
        file_name = f"photo_{user_id}.jpg"

    if file_id:
        r.hdel("waiting_for_training_file", str(user_id))
        print("training")
        handle_training_file(chat_id, file_id, file_name, user_id, user_name)
    else:
        send_message(chat_id, "❌ Please send a file or photo to train Myra.")

    return True


COMMANDS = {
    "/askmyra": cmd_askmyra,
    "/trainmyra": cmd_trainmyra,
}
