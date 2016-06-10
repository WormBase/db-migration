
from . import admin, awscloudops, install, runcommand
from . import root_command

# imported for side effect of command group population.
# Silence PEP8 linter
_ = admin, awscloudops, install, runcommand

cli = root_command(obj={})
