from fastapi.responses import RedirectResponse
import requests
import uvicorn
from fastapi import FastAPI, Response
from api123 import *
import mimetypes

app = FastAPI()
api = pan123Api()


def listDirHtml(pid):
    lis = []
    for file in api.listAllFiles(pid):
        if file["type"] == 0:
            lis.append(
                '<li><a href="{}">{}</a></li>'.format(
                    file["filename"], file["filename"]
                )
            )
        else:
            lis.append(
                '<li><a href="{}/">{}/</a></li>'.format(
                    file["filename"], file["filename"]
                )
            )
    return """<html lang="en"><head><meta charset="utf-8"><body><hr><ul>{}</ul><hr></body></html>""".format(
        "\n".join(lis)
    )


@app.get("/{path:path}")
async def read_path(path: str):
    if len(path) == 0:
        return Response(
            content=listDirHtml(0),
            headers={"content-type": "text/html; charset=utf-8"},
        )
    else:
        pid = api.getPathId("/" + path)
        detail = api.getFileDetail(pid)
        if detail["type"] == 1:
            return Response(
                content=listDirHtml(pid),
                headers={"content-type": "text/html; charset=utf-8"},
            )
        else:
            url = api.get302url(path)
            return RedirectResponse(url=url, status_code=302)


def get_content_type(file_name):
    content_type, _ = mimetypes.guess_type(file_name)
    print(f"{file_name}:{content_type}")
    return content_type or "application/octet-stream"


@app.head("/{path:path}")
async def process_url(path: str):
    if len(path) == 0:
        return Response(
            content=listDirHtml(0),
            headers={"content-type": "text/html; charset=utf-8"},
        )
    else:
        pid = api.getPathId("/" + path)
        detail = api.getFileDetail(pid)
        if detail["type"] == 1:
            return RedirectResponse(url=path + "/", status_code=301)
        else:
            return Response(
                headers={
                    "content-type": get_content_type(detail["filename"]),
                    "content-length": str(detail["size"]),
                    "last-modified": detail["updateAt"],
                },
            )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

