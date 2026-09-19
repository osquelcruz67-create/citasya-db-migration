import os, re, json
from pymongo import MongoClient

mongo_url = os.environ.get("MONGO_URL", "mongodb://mongodb.railway.internal:27017")
db_name = os.environ.get("DB_NAME", "citasya")
base = os.environ.get("MEDIA_BASE_URL", "https://viralmen-hub.preview.emergentagent.com")

print(f"Connecting to {mongo_url}/{db_name}...")
client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
db = client[db_name]

collections = db.list_collection_names()
print(f"Collections: {collections}")
print(f"Users: {db.users.count_documents({})}")
print(f"Videos: {db.videos.count_documents({})}")
print(f"Posts: {db.posts.count_documents({})}")

def fix_field(collection, field_name):
    count = 0
    cursor = collection.find({field_name: {"$regex": "^/api/uploads/"}})
    for doc in cursor:
        old = doc[field_name]
        new = base + old
        collection.update_one({"_id": doc["_id"]}, {"$set": {field_name: new}})
        print(f"  Fixed {field_name}: {old} -> {new}")
        count += 1
    return count

total = 0
for f in ["photo_url", "photoUrl", "avatar", "profile_photo", "profilePhoto"]:
    n = fix_field(db.users, f)
    if n: total += n

for user in db.users.find({"photos": {"$elemMatch": {"$regex": "^/api/uploads/"}}}):
    new_photos = [base + p if p.startswith("/api/uploads/") else p for p in user.get("photos", [])]
    db.users.update_one({"_id": user["_id"]}, {"$set": {"photos": new_photos}})
    print(f"  Fixed photos array for user {user.get('username', str(user['_id']))}")
    total += 1

print(f"\nFixed {total} user photo references")

vtotal = 0
for f in ["thumbnail_url", "thumbnailUrl", "video_url", "videoUrl", "url", "thumbnail", "media_url"]:
    n = fix_field(db.videos, f)
    if n: vtotal += n
print(f"Fixed {vtotal} video references")

ptotal = 0
for f in ["image_url", "imageUrl", "media_url", "mediaUrl", "thumbnail_url", "photo_url"]:
    n = fix_field(db.posts, f)
    if n: ptotal += n
print(f"Fixed {ptotal} post references")

print("\n=== VERIFICATION ===")
osquel = db.users.find_one({"username": {"$regex": "osquel", "$options": "i"}})
if osquel:
    print(f"User: {osquel.get('username')}")
    for f in ["photo_url", "photoUrl", "avatar", "profile_photo", "profilePhoto", "photos"]:
        if f in osquel:
            print(f"  {f}: {osquel[f]}")
else:
    print("Osquel user not found, showing first 3 users:")
    for u in db.users.find().limit(3):
        print(f"  User: {u.get('username', 'no-name')}")
        for f in ["photo_url", "photoUrl", "avatar", "profile_photo", "profilePhoto", "photos"]:
            if f in u:
                val = u[f]
                if isinstance(val, list):
                    val = val[:2]
                print(f"    {f}: {val}")

sample_vid = db.videos.find_one()
if sample_vid:
    print(f"\nSample video: {sample_vid.get('_id')}")
    for f in ["thumbnail_url", "thumbnailUrl", "video_url", "videoUrl", "url"]:
        if f in sample_vid:
            print(f"  {f}: {sample_vid[f]}")

print("\nMigration complete!")
client.close()
