
from . import root_command
from . import github
from . import admin, awscloudops, install, notifications, runcommand

# imported for side effect of command group population.
# Silence PEP8 linter
_ = admin, awscloudops, install, notifications, runcommand, github

cli = root_command(obj={})
