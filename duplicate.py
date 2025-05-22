#!/usr/bin/env python3
from io import BytesIO
from fastapi.responses import RedirectResponse
import requests
import uvicorn
from fastapi import FastAPI, Request, Response
from api123 import *
import mimetypes
import hashlib
import argparse
import json
import yaml


api = pan123Api()


dirID = api.getPathId("/test")
files = api.listAllFiles(dirID)

duplicate = {}

print("Checking for duplicate files...")

for file in files:
    if file["etag"] not in duplicate:
        duplicate[file["etag"]] = [file]
    else:
        duplicate[file["etag"]].append(file)
        
        
        
print("Duplicate files:")
for etag, file_list in duplicate.items():
    if len(file_list) > 1:
        print(f"ETag: {etag}")
        for file in file_list:
            print(f"  - {file['filename']} (ID: {file['fileId']})")

# 去掉数量为1的文件
duplicate = {k: [f'{x["fileId"]}/{x["filename"]}' for x in v] for k, v in duplicate.items() if len(v) > 1}
            
# with open("duplicate.json", "w") as f:
#     json.dump(duplicate, f, indent=2 ,ensure_ascii=False)

# 保存为yaml格式
with open("duplicate.yaml", "w") as f:
    yaml.dump(duplicate, f, allow_unicode=True, default_flow_style=False)


print("Duplicate files saved to duplicate.yaml")
print("Editing duplicate.yaml to remove files")
input("Press any key to continue...\n")
with open("duplicate.yaml", "r") as f:
    duplicate = yaml.safe_load(f)
for etag, file_list in duplicate.items():
    print(f"ETag: {etag}")
    print("Files to delete:")
    for file in file_list:
        fileid, filename = file.split("/")
        print(f"delete {filename} (ID: {fileid})")
if input("Are you sure you want to delete these files? (y/n)") == "y":
    fileIDs = []
    for etag, file_list in duplicate.items():
        for file in file_list:
            fileid, filename = file.split("/")
            res = api.delete_trash([int(fileid)])
            if res["code"] != 0:
                print(f"Error deleting {filename} (ID: {fileid}): {res['message']}")
            else:
                print(f"Deleted {filename}  success")