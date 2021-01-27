from urllib.parse import quote


DEFAULT_CHUNK_SIZE = 64 * 2 ** 10

def create_chunks(stream, chunk_size=DEFAULT_CHUNK_SIZE):
    stream.seek(0)
    while True:
        data = stream.read(chunk_size)
        if not data:
            break
        yield data


def filepath_to_uri(path):
    if path is None:
        return path
    
    return quote(path.replace("\\", "/"), safe="/~!*()'")