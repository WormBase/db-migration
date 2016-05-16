# Architecture

## Terraform

 * [Download terraform][1]
 
```bash
mkdir ${HOME}/terraform
cd ${HOME}/terraform
unzip $TERRAFORM_ZIP
export PATH="${HOME}/terraform:${PATH}"
```

## IAM setup

A group will contain common credentials for IAM users who will perform
the build. 

Each user will have the ability to [assume a role][3],
granting the user permission to run commands associated with build.

[1]: https://www.terraform.io/downloads.html
[3]: http://docs.aws.amazon.com/cli/latest/userguide/cli-roles.html

