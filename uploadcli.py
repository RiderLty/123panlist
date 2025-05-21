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


def md5_bytes(input_bytes):
    md5_hash = hashlib.md5()
    md5_hash.update(input_bytes)
    return md5_hash.hexdigest()

def md5_file(file_path):
    md5_hash = hashlib.md5()
    total_size = os.path.getsize(file_path)
    start = time.perf_counter_ns()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 64):
            md5_hash.update(chunk)
            print(f"{file_path} MD5SUM {(f.tell() * 100 / total_size):.2f}%", end="\r")
        end = time.perf_counter_ns()
        speed = (total_size /  1048576) / ((end - start ) / 1e9)
        print(f"{file_path} MD5SUM  {total_size /  1048576:.2f}MB in {(end - start ) / 1e9:.2f}s  {speed:.2f}MB/s")
    return md5_hash.hexdigest()

api = pan123Api()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="示例脚本")
    parser.add_argument("src", help="src文件路径")
    parser.add_argument("dst", help="dst网盘路径")

    args = parser.parse_args()
    dst = ""
    if args.dst == "":
        dst = "/"
    else:
        if args.dst[0] != "/":
            dst = "/" + args.dst
        else:
            dst = args.dst
    if dst[-1] != "/":
        dst = dst + "/"

    uploadmap = {}
    if os.path.isfile(args.src):
        target = dst + os.path.split(args.src)[1]
        uploadmap[args.src] = target
    else:
        target = dst + os.path.split(args.src)[1]
        for root, dirs, files in os.walk(args.src):
            for file in files:
                path = os.path.join(root, file)
                uploadmap[path] = os.path.join(target, os.path.relpath(path, args.src))
    for k, v in uploadmap.items():
        print("上传文件:", k)
        print("目标位置:", v)
        print("")

    if input("是否开始上传？(y/n)") == "y":
        parentIdMap = {}
        for k, v in uploadmap.items():
            parent, filename = os.path.split(v)
            if parent not in parentIdMap:
                try:
                    pid = api.getPathId(parent)
                    parentIdMap[parent] = pid
                except Exception as e:
                    pid = api.mkdirs(parent)
                    print("创建文件夹:", parent)
                    parentIdMap[parent] = pid
        for k, v in uploadmap.items():
            parent, filename = os.path.split(v)
            pid = parentIdMap[parent]
            print("上传文件:", k)
            print("目标位置:", v)
            api.uploadFile(open(k, "rb"), filename, pid, md5_file(k), os.path.getsize(k))
            print("上传完成\n")

    else:
        print("取消上传")
