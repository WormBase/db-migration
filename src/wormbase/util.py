import requests


def download(url, local_filename):
    response = requests.get(url)
    with open(local_filename, 'wb') as fp:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                fp.write(chunk)
    return fp.name

