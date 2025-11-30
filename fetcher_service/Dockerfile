FROM python:3.13-slim AS proto-builder

RUN pip install --no-cache-dir grpcio-tools==1.68.1

WORKDIR /app/protobuf

COPY protobuf/*.proto ./
RUN mkdir -p gen/python
RUN python -m grpc_tools.protoc -I. \
    --python_out=gen/python \
    --grpc_python_out=gen/python \
    *.proto

RUN sed -i 's/^import content_pb2/from . import content_pb2/' gen/python/services_pb2.py || true
RUN sed -i 's/^import content_pb2/from . import content_pb2/' gen/python/services_pb2_grpc.py || true

RUN touch gen/python/__init__.py
RUN touch gen/__init__.py

FROM python:3.13-slim

WORKDIR /app

COPY fetcher_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=proto-builder /app/protobuf protobuf

COPY fetcher_service/src ./src

ENV PYTHONPATH=/app

EXPOSE 8082

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8082"]
