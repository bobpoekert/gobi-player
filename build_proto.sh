#!/bin/sh
protoc --java_out=src/main/java/ --python_out=python/src/ python.proto
