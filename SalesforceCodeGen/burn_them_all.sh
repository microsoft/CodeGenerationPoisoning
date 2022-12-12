#!/bin/bash
docker rm --force $(docker ps -a -q)
