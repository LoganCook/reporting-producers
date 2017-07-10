import uuid

def generate_payload(data, metadata=None):
    # config is a basic collector config from producer package
    # or a config of pusher.py
    payload = {"id": str(uuid.uuid4()),
               "session": str(uuid.uuid4()),
               "data": data
              }
    if metadata:
        for meta in metadata:
            payload[meta] = metadata[meta]
    return payload
