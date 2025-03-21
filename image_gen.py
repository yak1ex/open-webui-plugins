"""
title: Image Gen Plus
author: open-webui, yak_ex
author_url: https://github.com/yak1ex/
git_url: https://github.com/yak1ex/open-webui-plugins.git
version: 0.2
required_open_webui_version: 0.5.3
"""

import os
import requests
from datetime import datetime
from typing import Callable
from fastapi import Request

from open_webui.routers.images import image_generations, GenerateImageForm
from open_webui.models.users import Users


class Tools:
    def __init__(self):
        self.citation = False

    async def generate_image(
        self, prompt: str, __request__: Request, __user__: dict, __id__: str, __event_emitter__=None
    ) -> str:
        """
        Generate an image according to a given prompt

        :param prompt: prompt to use for image generation
        """

        await __event_emitter__(
            {
                "type": "status",
                "data": {"description": "Generating an image", "done": False},
            }
        )

        try:
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

            for image in images:
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": f"![Generated Image]({image['url']})"},
                    }
                )
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
                                "url": f"{image['url']}"
                            }
                        }
                    }
                )

            return f"Done."

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"An error occured: {e}", "done": True},
                }
            )

            return f"Tell the user: {e}"
