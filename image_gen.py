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
from typing import Awaitable, Callable
from fastapi import Request

import socketio

from open_webui.utils.auth import create_token
from open_webui.routers.images import image_generations, GenerateImageForm
from open_webui.models.chats import Chats
from open_webui.models.users import Users
from open_webui.tasks import create_task
from open_webui.env import (
    ENABLE_WEBSOCKET_SUPPORT,
)

Emitter = Awaitable[None]

wait_queue: dict[tuple[str, str], Emitter] = {}
sio = socketio.AsyncClient()


async def nop() -> None:
    pass


def register_emitter(chat_id: str, message_id: str, emitter: Emitter) -> None:
    """
    Register an emitter for a given chat id and message id.
    """
    wait_queue[(chat_id, message_id)] = emitter


def get_emitter(chat_id: str, message_id: str) -> Emitter:
    """
    Get the emitter for a given chat id and message id.
    """
    return wait_queue.pop((chat_id, message_id), nop())


@sio.on("chat-events")
async def queue_handler(data) -> None:
    """
    Call a registered emitter for a completed message
    """
    print(f"queue_handler {data=}")
    event_data = data.get("data", {})
    if (
        "chat_id" in data
        and "message_id" in data
        and event_data.get("type", "") == "chat:completion"
        and event_data.get("data", {}).get("done", False) == True
    ):
        await asyncio.sleep(0.5)
        await get_emitter(data["chat_id"], data["message_id"])


class Tools:
    def __init__(self):
        self.citation = False

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
                    "http://localhost:8080",
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

            async def emitter():
                print("emitter() called")
                for image in images:
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {
                                "content": f"![Generated Image]({image['url']} \"{prompt}\")"
                            },
                        }
                    )
                    print(f"![Generated Image]({image['url']} \"{prompt}\")")
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {
                                "document": [f"{image['url']}"],
                                "metadata": [
                                    {
                                        "source": f"{image['url']}",
                                        "prompt": prompt,
                                    }
                                ],
                                "source": {
                                    "name": f"TOOL:{__id__}/generate_image with prompt: {prompt}",
                                    "url": f"{image['url']}",
                                },
                            },
                        }
                    )

            if native:
                register_emitter(
                    __metadata__["chat_id"], __metadata__["message_id"], emitter()
                )
            else:
                await emitter()

            return f"Done."

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"An error occured: {e}", "done": True},
                }
            )

            return f"Tell the user: {e}"
