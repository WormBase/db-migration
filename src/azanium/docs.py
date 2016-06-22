from . import util


def build_and_deploy(data):
    util.local('make docs')
    util.local('make deploy-docs')
