# 123PanList

## 能做什么

将123pan挂载为http服务，可用于rclone，alist等网盘程序

## 为什么要整这个

更快的遍历目录文件

官网webdav 4分10秒

![alt text](data/4dcc76cc10025e60d88da4ef134a2e81.png)

官方api 25秒

![alt text](data/ccd6234f7b091d6957a574d5160c6b50.png)

[目录信息](data/tree.txt)
## 如何使用

前往[123云盘开放平台](https://www.123pan.com/developer)申请成为开发者，获取clientID与clientSecret

前往123云盘主页

工具中心 > 第三方挂载 > WebDAV授权管理 > 添加应用 > 生成密码

访问 [https://webdav-1833788059.pd1.123pan.cn/webdav](https://webdav-1833788059.pd1.123pan.cn/webdav)

登录后，F12，找到请求标头中的Authorization值,形如

```
Basic MTUyNTU***********************************************dmM3Y=
```

执行
```
docker run -d --name=123panlist --restart=unless-stopped \
  -e CLIENT_ID=<你的clientID> \
  -e CLIENT_SECRET=<你的clientSecret> \
  -e WEBDAV_AUTH='<webdav的Authorization值>' \
  -p 8000:8000 
  riderlty/123panlist
```

使用Rclone等工具添加http后端即可