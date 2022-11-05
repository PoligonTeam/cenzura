from femcord.httpclient import HTTPClient
from femcord.httpclient.webservers.aiohttpserver import WebServer
import logging

logging.basicConfig(level=logging.DEBUG)

client = HTTPClient(
    WebServer,
    client_id = "963561563690762320",
    client_secret = "WSUPVuljFpaePncWXl1poggjmzaP38Dv",
    public_key = "b9fd3d0c6294fa06884bec390e2daaa02e01e9b4ced39c6142a7e2c2b7d51abd",
    interaction_endpoint = "/interactions"
)

client.run("OTYzNTYxNTYzNjkwNzYyMzIw.GDD6_B.zAXx5GqkM_n2EKRZMy5OUFL2mXoC3uKxSF52z0", host="127.0.0.1", port=3200)