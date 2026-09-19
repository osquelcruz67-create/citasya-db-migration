import os
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

# Fix ALL possible user photo fields
total = 0
for f in ["photo_url", "photoUrl", "avatar", "profile_photo", "profilePhoto", "picture", "user_picture", "user_photo"]:
    n = fix_field(db.users, f)
    if n:
        total += n
        print(f"  -> Fixed {n} users for field {f}")

# Fix photos array
for user in db.users.find({"photos": {"$elemMatch": {"$regex": "^/api/uploads/"}}}):
    new_photos = [base + p if p.startswith("/api/uploads/") else p for p in user.get("photos", [])]
    db.users.update_one({"_id": user["_id"]}, {"$set": {"photos": new_photos}})
    print(f"  Fixed photos array for user {user.get('username', user.get('name', str(user['_id'])))}")
    total += 1

print(f"\nFixed {total} user photo references")

# Fix ALL possible video fields
vtotal = 0
for f in ["thumbnail_url", "thumbnailUrl", "video_url", "videoUrl", "url", "thumbnail", "media_url", "user_picture", "user_photo"]:
    n = fix_field(db.videos, f)
    if n:
        vtotal += n
        print(f"  -> Fixed {n} videos for field {f}")
print(f"Fixed {vtotal} video references")

# Fix posts
ptotal = 0
for f in ["image_url", "imageUrl", "media_url", "mediaUrl", "thumbnail_url", "photo_url", "picture", "user_picture"]:
    n = fix_field(db.posts, f)
    if n:
        ptotal += n
print(f"Fixed {ptotal} post references")

# Fix comments user photos
ctotal = 0
for f in ["user_picture", "user_photo", "photo_url", "picture"]:
    n = fix_field(db.comments, f)
    if n:
        ctotal += n
print(f"Fixed {ctotal} comment references")

# Fix lives
ltotal = 0
for f in ["thumbnail_url", "user_picture", "user_photo", "host_picture", "picture"]:
    n = fix_field(db.lives, f)
    if n:
        ltotal += n
print(f"Fixed {ltotal} lives references")

# Fix notifications
ntotal = 0
for f in ["sender_picture", "user_picture", "picture", "photo_url"]:
    n = fix_field(db.notifications, f)
    if n:
        ntotal += n
print(f"Fixed {ntotal} notification references")

print("\n=== VERIFICATION ===")
print("\nFirst 5 users with photo_url:")
for u in db.users.find({"photo_url": {"$exists": True, "$ne": None, "$ne": ""}}).limit(5):
    print(f"  {u.get('name', u.get('username', str(u['_id'])))}: photo_url={u.get('photo_url', 'N/A')}")
    if 'picture' in u:
        print(f"    picture={u.get('picture')}")

print("\nFirst 3 videos with video_url:")
for v in db.videos.find({"video_url": {"$exists": True}}).limit(3):
    print(f"  {v.get('_id')}: video_url={v.get('video_url', 'N/A')}, thumbnail={v.get('thumbnail_url', 'N/A')}")

# Check for any remaining relative URLs across all collections
print("\n=== REMAINING RELATIVE URLS CHECK ===")
for coll_name in collections:
    coll = db[coll_name]
    sample = coll.find_one()
    if sample:
        for key, val in sample.items():
            if isinstance(val, str) and val.startswith("/api/uploads/"):
                count = coll.count_documents({key: {"$regex": "^/api/uploads/"}})
                print(f"  WARNING: {coll_name}.{key} still has {count} relative URLs")

print("\nMigration complete!")
client.close()
