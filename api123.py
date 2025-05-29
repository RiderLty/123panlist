from io import BufferedReader
import os
import time
import requests
import math
import shlex
import subprocess
from cachetools import TTLCache
import base64


def get_key(KEY_NAME):
    if os.environ.get(KEY_NAME) != None:
        return os.environ.get(KEY_NAME)
    key_file = os.path.join(os.path.dirname(__file__), KEY_NAME)
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="UTF-8") as f:
            return f.read()
    raise FileNotFoundError(f"{KEY_NAME} not set !")


def generate_authorization_header(username, password):
    encoded_credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {encoded_credentials}"


def validToken(token):
    resp = requests.get(
        "https://open-api.123pan.com/api/v2/file/list",
        data={
            "parentFileId": 0,
            "limit": 1,
        },
        headers={
            "Authorization": token,
            "Platform": "open_platform",
        },
    ).json()
    assert resp["code"] == 0, resp["message"]


def execute_command(command_with_args, dry_run=False):
    try:
        if dry_run:
            return {
                "code": 0,
                "out": command_with_args,
                "error": "",
            }
        else:
            proc = subprocess.Popen(
                shlex.split(command_with_args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, stderr = proc.communicate()
            return {
                "code": proc.returncode,
                "out": stdout.replace("\\n", "\n"),
                "error": stderr,
            }
    except FileNotFoundError as not_found_e:
        return {
            "code": -20,
            "out": "",
            "error": not_found_e,
        }
    except Exception as generic_e:
        return {
            "code": -30,
            "out": "",
            "error": generic_e,
        }


class pan123Api:
    def __init__(self, ttl=30) -> None:
        self.session = requests.session()
        self.host = "https://open-api.123pan.com"
        self.idCache = TTLCache(maxsize=0xFFFFFFFF, ttl=ttl)
        self.treeCache = TTLCache(maxsize=0xFFFFFFFF, ttl=ttl)
        self.urlCache = TTLCache(maxsize=0xFFFFFFFF, ttl=ttl)
        self.token = self.refreshToken()
        self.headers = {
            "Authorization": self.token,
            "Platform": "open_platform",
        }
        self.webdav_auth = generate_authorization_header(get_key("WEBDAV_ACCOUNT"), get_key("WEBDAV_SECRITE"))
        self.webdav_host = get_key("WEBDAV_HOST")
        if not self.webdav_host.endswith("/"):
            self.webdav_host = self.webdav_host + "/"

    def refreshToken(self) -> str:
        try:
            with open(os.path.join(os.path.dirname(__file__), "accessToken"), "r", encoding="UTF-8") as f:
                token = f.read()
            validToken(token)
            return token
        except Exception as e:
            print(e)
        try:
            resp = requests.post(
                "https://open-api.123pan.com/api/v1/access_token",
                data={
                    "clientID": get_key("CLIENT_ID"),
                    "clientSecret": get_key("CLIENT_SECRET"),
                },
                headers={
                    "Platform": "open_platform",
                },
            ).json()
            assert resp["code"] == 0, resp["message"]
            token = resp["data"]["accessToken"]
            validToken(token)
            with open(os.path.join(os.path.dirname(__file__), "accessToken"), "w", encoding="UTF-8") as f:
                f.write(token)
            print("token 已刷新")
            return token
        except Exception as e:
            print(e)
        exit(1)

    def get(self, url, data):
        return self.session.get(url=self.host + url, data=data, headers=self.headers)

    def post(self, url, data):
        return self.session.post(url=self.host + url, data=data, headers=self.headers)

    def getFileDetail(self, fileID):
        if fileID in self.idCache:
            self.idCache[fileID] = self.idCache[fileID]
            return self.idCache[fileID]
        result = self.get(url="/api/v1/file/detail", data={"fileID": fileID}).json()
        assert result["code"] == 0, result["message"]
        self.idCache[fileID] = result["data"]
        return result["data"]

    def listFiles(self, parentFileId, limit=100, searchData=None, searchMode=None, lastFileId=None):
        return self.get(
            url="/api/v2/file/list",
            data={
                "parentFileId": parentFileId,
                "limit": limit,
                "searchData": searchData,
                "searchMode": searchMode,
                "lastFileId": lastFileId,
            },
        ).json()

    def listAllFiles(self, parentFileId):
        if parentFileId in self.treeCache:
            self.treeCache[parentFileId] = self.treeCache[parentFileId]
            res = []
            allCached = True
            for x in self.treeCache[parentFileId]:
                if x in self.idCache:
                    self.idCache[x] = self.idCache[x]
                    res.append(self.idCache[x])
                else:
                    allCached = False
                    break
            if allCached:
                return res
        lastFileId = None
        files = []
        while lastFileId != -1:
            res = self.listFiles(parentFileId=parentFileId, limit=100, lastFileId=lastFileId)
            if res["code"] == 0:
                lastFileId = res["data"]["lastFileId"]
                for file in res["data"]["fileList"]:
                    if file["trashed"] == 0:
                        files.append(file)
                        self.idCache[file["fileId"]] = file  # 缓存
            else:
                print(res["message"], "等待1s后重试")
                time.sleep(1)

        self.treeCache[parentFileId] = [x["fileId"] for x in files]
        return files

    def getDownloadUrl(self, fileID):
        """
        获取下载信息
        fileID: 文件ID
        """
        result = self.get(url="/api/v1/file/download_info", data={"fileID": fileID}).json()
        assert result["code"] == 0, result["message"]
        return result["data"]["downloadUrl"]
    
    def getPathId(self, path):
        """
        获取文件夹的ID
        路径必须以/开头
        文件夹必须存在
        """
        if path == "/":
            return 0
        assert path[:1] == "/"
        parts = path.split("/")
        fileIdMap = []
        parentId = 0
        for part in parts:
            if part == "":
                continue
            flag = False
            for file in self.listAllFiles(parentId):
                if file["filename"] == part:
                    fileIdMap.append(file["fileId"])
                    parentId = file["fileId"]
                    flag = True
            assert flag == True, f"未找到文件夹:{part}"
        return parentId

    def get302url_dav(self, path):
        if path in self.urlCache:
            self.urlCache[path] = self.urlCache[path]
            return self.urlCache[path]
        start = time.perf_counter_ns()
        req = requests.get(
            f"{self.webdav_host}{path}",
            headers={
                "Authorization": self.webdav_auth,
                "range": "bytes=0-0",
            },
        )
        end = time.perf_counter_ns()
        print(f"webdav 获取下载信息耗时: {(end - start) / 1000000}ms")
        self.urlCache[path] = req.url
        return req.url
    
    def get302url(self, path):
        if path in self.urlCache:
            self.urlCache[path] = self.urlCache[path]
            return self.urlCache[path]
        parentId = self.getPathId("/"+os.path.split(path)[0])
        files = self.listAllFiles(parentFileId=parentId)
        filename = os.path.split(path)[-1]
        assert filename != "", "文件名不能为空"
        for file in files:
            if file["filename"] == filename:
                start = time.perf_counter_ns()
                url = self.getDownloadUrl(fileID=file["fileId"])
                end = time.perf_counter_ns()
                print(f"api 获取下载信息耗时: {(end - start) / 1000000}ms")  
                self.urlCache[path] = url
                return url          
        raise FileNotFoundError(f"未找到文件或文件夹: {path}")

    def direct_link(self, fileID):
        return self.get(
            url="/api/v1/direct-link/url",
            data={
                "fileID": fileID,
            },
        ).json()

    def mkdir(self, name, parentID):
        return self.post(url="/upload/v1/file/mkdir", data={"name": name, "parentID": parentID}).json()

    def mkdirs(self,path):
        """
        path 绝对路径
        """
        assert path[:1] == "/" , "路径必须以/开头"
        parts = path.split("/")
        parentId = 0
        parentExistFlag = True
        for part in parts:
            if part == "":
                continue
            if parentExistFlag == True:# 如果上级目录存在
                flag = False
                for file in self.listAllFiles(parentId):
                    if file["filename"] == part:
                        parentId = file["fileId"]
                        flag = True
                        break
                if flag == True:# 在上级目录中找到了此文件夹
                    pass
                else:
                    self.treeCache.clear()
                    self.idCache.clear()
                    parentExistFlag = False
                    parentId = self.mkdir(name=part, parentID=parentId)["data"]["dirID"]
            else:
                parentId = self.mkdir(name=part, parentID=parentId)["data"]["dirID"]
        return parentId


    def uploadCreate(self, parentFileID, filename, etag, size):
        return self.post(
            url="/upload/v1/file/create",
            data={
                "parentFileID": parentFileID,
                "filename": filename,
                "etag": etag,
                "size": size,
            },
        ).json()

    def uploadComplete(self, preuploadID):
        return self.post(
            url="/upload/v1/file/upload_complete",
            data={
                "preuploadID": preuploadID,
            },
        ).json()

    def uploadGetUploadURL(self, preuploadID, sliceNo):
        return self.post(
            url="/upload/v1/file/get_upload_url",
            data={"preuploadID": preuploadID, "sliceNo": sliceNo},
        ).json()

    def listUploadParts(self, preuploadID):
        return self.post(
            url="/upload/v1/file/list_upload_parts",
            data={"preuploadID": preuploadID},
        ).json()

    def uploadListUploadParts(self, preuploadID):
        return self.post(url="/upload/v1/file/list_upload_parts", data={"preuploadID": preuploadID}).json()

    def uploadAsyncResult(self, preuploadID):
        return self.post(url="/upload/v1/file/upload_async_result", data={"preuploadID": preuploadID}).json()

    def uploadFile(self, fileLike: BufferedReader, filename, parentId, md5, size):
        """
        fileLike  rb 可read seek 的对象
        remotePath 远程绝对路径 /开头
        路径必定已存在
        md5  文件总长度
        """
        create = self.uploadCreate(parentId, filename, md5, size)
        assert create["code"] == 0, create["message"]
        if create["data"]["reuse"] == True:
            print("秒传成功")
            return
        else:
            print("秒传失败")
            sliceProgress = {}
            sliceSize = create["data"]["sliceSize"]
            preuploadID = create["data"]["preuploadID"]

            print(f"分片大小{sliceSize // 1048576}MB")
            print(f"分片数{ math.ceil(size / sliceSize) }")
            for i in range(math.ceil(size / sliceSize)):
                sliceProgress[i + 1] = False

            preloaded = self.uploadListUploadParts(preuploadID)
            print("preloaded")
            print(preloaded)
            for part in preloaded["data"]["parts"]:
                sliceProgress[part["partNumber"]] = True
                print(f'分片{part["partNumber"]}已上传,大小{part["size"] // 1048576}MB,MD5:{part["etag"]}')
            for keyIndex in sliceProgress.keys():
                if sliceProgress[keyIndex] == True:
                    print(f"分片{keyIndex}已跳过")
                    continue
                url = self.uploadGetUploadURL(preuploadID=preuploadID, sliceNo=keyIndex)
                presignedURL = url["data"]["presignedURL"]
                fileLike.seek(sliceSize * (keyIndex - 1))
                bytes = fileLike.read(sliceSize)
                print(f"分片{keyIndex}，读取了{len(bytes)}字节，上传中")
                print(presignedURL)
                requests.put(url=presignedURL, data=bytes)
                print("上传完成")
            res = self.listUploadParts(preuploadID)
            print(res)
            res = self.uploadAsyncResult(preuploadID)
            print(res)
            res = self.uploadComplete(preuploadID)
            print(res)
            print("全部完成")
            # self.uploadCreate(0, "random.img", "32d4846a4f88a350efe79481ffce29cd", 1073741824)
    
    def delete_trash(self, fileIDs):#虽然官方说是删除100个，但是实际只能删除1个
        assert isinstance(fileIDs, list), "fileIDs must be a list"
        assert len(fileIDs) > 0 and len(fileIDs) < 1000, "fileIDs must be a list of length 1-1000"
        return self.post(
            url="/api/v1/file/trash",
            data={
                "fileIDs": fileIDs,
            },
        ).json()
    
    
    # # def put(self):
    # #     requests.put()

    # def lsjson(self, parentId, rootPath="", maxDeepth=-1, deepth=0):
    #     # 不整多线程了，减轻点服务器压力
    #     print(rootPath)
    #     if maxDeepth != -1 and deepth == maxDeepth:
    #         return []
    #     currentFiles = self.listAllFiles(parentFileId=parentId)
    #     for i in range(len(currentFiles)):
    #         currentFiles[i]["filePath"] = f'{rootPath}/{currentFiles[i]["filename"]}'
    #     dirList = [x for x in currentFiles if x["type"] == 1]
    #     for x in dirList:
    #         currentFiles.extend(
    #             self.lsjson(
    #                 x["fileId"],
    #                 rootPath=x["filePath"],
    #                 maxDeepth=maxDeepth,
    #                 deepth=deepth + 1,
    #             )
    #         )
    #     return currentFiles
