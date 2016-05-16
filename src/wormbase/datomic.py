from . import util

def download(version):
    url = 'https://my.datomic.com/downloads/free/{}'
    url = url.format(version)
    local_filename = 'datomic-free_{version}'.format(version)
    return util.download(url, local_filename)

def install():
    pass

def start_transactor():
    pass

def stop_transactor():
    pass

