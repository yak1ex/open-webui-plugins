"""
title: Repeat Input Action
author: yak_ex
author_url: https://github.com/yak1ex/
git_url: https://github.com/yak1ex/open-webui-plugins.git
version: 0.0.1
required_open_webui_version: 0.3.9
"""

from pydantic import BaseModel, Field
from typing import Optional, Union, Generator, Iterator

import os
import requests
import asyncio

from open_webui.utils.misc import get_last_user_message

class Action:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()
        pass

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> Optional[dict]:
        print(f"action:{__name__}")
        print(body)

        content = get_last_user_message(body["messages"])

        response = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": "modify a message",
                    "message": "here write a message to append",
                    "value": content,
                },
            }
        )
        print(response)

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "adding message", "done": False},
                }
            )
            await asyncio.sleep(1)
            response = response.replace("$", "\\$")
            await __event_emitter__(
                {
                    "type": "execute",
                    "data": {"code": f'postMessage({{"type":"input:prompt", "text": String.raw`{response}`}})'}
                } 
            )
            await __event_emitter__(
                {
                    "type": "execute",
                    "data": {"code": f'postMessage({{"type":"input:prompt:submit", "text": String.raw`{response}`}})'}
                } 
            )
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "added message", "done": True},
                }
            )
