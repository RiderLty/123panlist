# # 这个最小 但是只有amd64成功了
FROM python:3.11.2-alpine
# FROM python:3.9-alpine
COPY api123.py pan123list.py requirements.txt /
WORKDIR /
RUN pip install -r /requirements.txt 
CMD ["python", "/pan123list.py"]