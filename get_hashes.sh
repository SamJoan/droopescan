#!/bin/bash

# This script must be run within a drupal git repo

if [ $# -ne 2 ]; then
	echo "Usage: $0 file_path output"
	exit
fi

file_path=$1
output_file=$2

for tag in $(git tag --sort=v:refname); do 
	if git cat-file blob $tag:$file_path &> /dev/null; then 
		echo \<version md5=\"$(git cat-file blob $tag:$file_path | md5sum | head -c -4;)\" nb=\"$tag\" /\>;
	fi;
done 2> /dev/null > $output_file
