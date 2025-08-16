from flask import Response

def stream_bytes(iterable, headers: dict):
    return Response(iterable, headers=headers)
