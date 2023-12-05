import hashlib

def hash(fpath):
  with open(fpath, "rb") as f:
    fhash = hashlib.md5()
    while chunk := f.read(8192):
      fhash.update(chunk)

  return fhash.hexdigest()

def http2https(url):
  return url.replace("http:", "https:")