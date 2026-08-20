import asyncio
import json
import math
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import websockets


HOST = "0.0.0.0"
HTTP_PORT = 8000
WS_PORT = 8765

players = {}
connections = set()


class WebHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def start_http():
    server = ThreadingHTTPServer((HOST, HTTP_PORT), WebHandler)
    print(f"Game website: http://localhost:{HTTP_PORT}")
    server.serve_forever()


async def broadcast():
    if not connections:
        return

    data = json.dumps({
        "type": "players",
        "players": list(players.values())
    })

    dead = []

    for connection in connections:
        try:
            await connection.send(data)
        except Exception:
            dead.append(connection)

    for connection in dead:
        connections.discard(connection)


async def game_loop():
    while True:
        await broadcast()
        await asyncio.sleep(1 / 30)


async def player_connection(websocket):
    player_id = str(id(websocket))

    player = {
        "id": player_id,
        "x": 400,
        "y": 300,
        "angle": 0,
        "hp": 100,
        "color": "#42a5f5"
    }

    players[player_id] = player
    connections.add(websocket)

    try:
        await websocket.send(json.dumps({
            "type": "welcome",
            "id": player_id
        }))

        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "move":
                player["x"] = max(
                    20,
                    min(1180, float(data.get("x", player["x"])))
                )

                player["y"] = max(
                    20,
                    min(680, float(data.get("y", player["y"])))
                )

                player["angle"] = float(
                    data.get("angle", player["angle"])
                )

            elif data.get("type") == "shoot":
                # Basic projectile event.
                # Add your own collision/damage system here.
                await broadcast()

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        connections.discard(websocket)
        players.pop(player_id, None)


async def websocket_server():
    async with websockets.serve(
        player_connection,
        HOST,
        WS_PORT
    ):
        print(f"WebSocket server: ws://localhost:{WS_PORT}")
        await game_loop()


def main():
    http_thread = threading.Thread(
        target=start_http,
        daemon=True
    )
    http_thread.start()

    asyncio.run(websocket_server())


if __name__ == "__main__":
    main()
