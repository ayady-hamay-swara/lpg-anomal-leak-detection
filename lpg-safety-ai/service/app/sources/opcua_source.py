from app.sources.base import DataSource

class OpcUaSource(DataSource):
    def get_frame(self):
        raise NotImplementedError("OPC UA real-plant adapter is not implemented or approved in V1")
