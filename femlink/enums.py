from enum import Enum

class Opcodes(Enum):
    READY = "ready"
    PLAYER_UPDATE = "playerUpdate"
    STATS = "stats"
    EVENT = "event"

class Events(Enum):
    TRACK_START = "TrackStartEvent"
    TRACK_END = "TrackEndEvent"
    TRACK_EXCEPTION = "TrackExceptionEvent"
    TRACK_STUCK = "TrackStuckEvent"
    WEBSOCKET_CLOSED = "WebSocketClosedEvent"

class LoadResultType(Enum):
    TRACK = "track"
    PLAYLIST = "playlist"
    SEARCH = "search"
    EMPTY = "empty"
    ERROR = "error"