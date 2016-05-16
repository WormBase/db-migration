provider "aws" {
  region = "${var.region}"
}

resource "aws_instance" "wb-db-build" {
  ami = "ami-408c7f28"
  instance_type = "t1.micro"
  tags = {
    CreatedBy = "${var.profile}"
  }
}

