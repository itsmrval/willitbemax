import grpc
import logging
from protobuf.gen.python import services_pb2, services_pb2_grpc

logger = logging.getLogger(__name__)

class DataSchedulerClient:
    def __init__(self, uri: str):
        self.channel = grpc.insecure_channel(uri)
        self.stub = services_pb2_grpc.DataSchedulerServiceStub(self.channel)

    def write_seasons(self, seasons_data):
        try:
            return self.stub.WriteSeasons(seasons_data)
        except grpc.RpcError as e:
            logger.error(f"Write error: {e}")
            raise

    def get_seasons(self, year=None, status=None):
        try:
            filter_req = services_pb2.SeasonsFilter()
            if year:
                filter_req.year = year
            if status:
                filter_req.status = status
            return self.stub.GetSeasons(filter_req)
        except grpc.RpcError as e:
            logger.error(f"Get error: {e}")
            raise

    def health(self) -> bool:
        try:
            self.stub.GetSeasons(services_pb2.SeasonsFilter(), timeout=5.0)
            return True
        except Exception:
            return False

    def close(self):
        self.channel.close()
