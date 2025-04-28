"""
title: Image Gen Plus
author: open-webui, justinrahb, yak_ex
author_url: https://github.com/yak1ex/
git_url: https://github.com/yak1ex/open-webui-plugins.git
version: 0.2
required_open_webui_version: 0.5.3
"""

"""
This is the modified version of the Image Gen(0.5.3+)
https://openwebui.com/t/justinrahb/image_gen released by justinrahb.

"""

import asyncio
import os
import re
import requests
from datetime import datetime
from typing import Awaitable, Callable, NamedTuple
from fastapi import Request
from pydantic import BaseModel, Field
import socketio

from open_webui.utils.auth import create_token
from open_webui.routers.images import image_generations, GenerateImageForm
from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.tasks import create_task
from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
)

class Entry(NamedTuple):
    emitter: Callable[[dict], Awaitable[None]]
    id: str
    images: list[dict]
    prompt: str


wait_queue: dict[tuple[str, str], list[Entry]] = {}
sio = socketio.AsyncClient()
parital_update: bool


def has_queue_entry(chat_id: str, message_id: str) -> bool:
    """
    Check if there is a queue entry for a given chat id and message id.
    """
    return (chat_id, message_id) in wait_queue


def has_queue_entry_of_data(data: dict) -> bool:
    """
    Check if there is a queue entry for a given data.
    """
    return (
        "chat_id" in data
        and "message_id" in data
        and has_queue_entry(
            data["chat_id"], data["message_id"])
    )


def is_clearing_chat_completion(data: dict) -> bool:
    return (
        data.get("data", {}).get("type", "") == "chat:completion" and
        "content" in data.get("data", {}).get("data", {}))


def is_completed(data: dict) -> bool:
    return data.get("data", {}).get("data", {}).get("done", False)


def append_queue_entry(chat_id: str, message_id: str, entry: Entry) -> None:
    """
    Append an entry to the queue for a given chat id and message id.
    """
    wait_queue.setdefault((chat_id, message_id), []).append(entry)


def get_queue_entry(chat_id: str, message_id: str) -> list[Entry]:
    """
    Get the queue entry for a given chat id and message id.
    """
    return wait_queue.get((chat_id, message_id), [])


def pop_queue_entry(chat_id: str, message_id: str) -> list[Entry]:
    """
    Pop the queue entry for a given chat id and message id.
    """
    return wait_queue.pop((chat_id, message_id), [])


def set_parital_update(value: bool) -> None:
    """
    Set the value of parital_update.
    """
    global parital_update
    parital_update = value


def get_parital_update() -> bool:
    """
    Get the value of parital_update.
    """
    global parital_update
    return parital_update


async def emitter(entries: list[Entry], completed: bool) -> None:
    print("emitter() called")
    content = "\n".join(
        f"![Generated Image]({image['url']} \"{entry.prompt}\")"
        for entry in entries for image in entry.images
    )
    await entries[-1].emitter(
        {
            "type": "message",
            "data": {
                "content": content
            },
        }
    )
    print(content)
    if completed:
        for entry in entries:
            for image in entry.images:
                await entry.emitter(
                    {
                        "type": "citation",
                        "data": {
                            "document": [f"{image['url']}"],
                            "metadata": [
                                {
                                    "source": f"{image['url']}",
                                    "prompt": entry.prompt,
                                }
                            ],
                            "source": {
                                "name": f"TOOL:{entry.id}/generate_image with prompt: {entry.prompt}",
                                "url": f"{image['url']}",
                            },
                        },
                    }
                )


@sio.on("chat-events")
async def queue_handler(data) -> None:
    """
    Call a registered emitter for a completed message
    """
    print(f"queue_handler {data=}")
    if is_clearing_chat_completion(data) and has_queue_entry_of_data(data):
        completed = is_completed(data)
        if get_parital_update() or completed:
            queue_entry = pop_queue_entry if completed else get_queue_entry
            await asyncio.sleep(0.5)
            entries = queue_entry(data["chat_id"], data["message_id"])
            await emitter(entries, completed)


class Tools:
    class Valves(BaseModel):
        WEBUI_BACKEND_HOST: str = Field(
            default=os.environ.get('HOST', 'localhost'),
            description=(
                "Host to connect to check if a native function calling completed. "
                "Default is a value of an environment variable `HOST`, or `localhost` if not set."
            ),
        )
        WEBUI_BACKEND_PORT: int = Field(
            default=os.environ.get('PORT', 8080),
            description=(
                "Port to connect to check if a native function calling completed. "
                "Default is a value of an environment variable `PORT`, or `8080` if not set."
            ),
        )
        PARTIAL_UPDATE: bool = Field(
            default=True,
            description=(
                "Enable partial update when multiple images are generating. "
                "If true, flushing occurs by repeated update."
            ),
        )

    def __init__(self):
        self.citation = False
        self.valves = self.Valves()

    async def generate_image(
        self,
        prompt: str,
        __request__: Request,
        __user__: dict,
        __id__: str,
        __event_emitter__=None,
        __model__=None,
        __metadata__=None,
        __messages__=None,
    ) -> str:
        """
        Generate an image by passing a textual prompt given by parameter
        to an external image generator.
        If you are asked to generate an image, you can use this tool.
        The result of the generated image is shown to a user automatically.
        So, you don't need to add URL or file content.
        If the input from the user is not in detail, in general,
        it is recommended to add description in detail in varirous aspects,
        such as color, style, feature of main topic, background and so on.

        :param prompt: textual description for the image to be generated,
                       which is passed to external image generator.
        """
        native = __metadata__.get("function_calling", "") == "native"
        print(native)
        set_parital_update(self.valves.PARTIAL_UPDATE)

        await __event_emitter__(
            {
                "type": "status",
                "data": {"description": "Generating an image", "done": False},
            }
        )

        try:
            if not sio.connected:
                print(f"{__user__=}")
                await sio.connect(
                    f"http://{self.valves.WEBUI_BACKEND_HOST}:{self.valves.WEBUI_BACKEND_PORT}",
                    socketio_path="/ws/socket.io",
                    auth={"token": create_token({"id": __user__.get("id")})},
                    transports=(
                        ["websocket"] if ENABLE_WEBSOCKET_SUPPORT else ["polling"]
                    ),
                )
                # sio.on("chat-events", queue_handler)

            images = await image_generations(
                request=__request__,
                form_data=GenerateImageForm(**{"prompt": prompt}),
                user=Users.get_user_by_id(__user__["id"]),
            )
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Generated an image", "done": True},
                }
            )
            print(images)

            entry = Entry(
                emitter=__event_emitter__,
                id=__id__,
                images=images,
                prompt=prompt
            )
            if native:
                append_queue_entry(
                    __metadata__["chat_id"],
                    __metadata__["message_id"],
                    entry
                )
            else:
                await emitter([entry], True)

            return f"Done."

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"An error occured: {e}", "done": True},
                }
            )

            return f"Tell the user: {e}"
