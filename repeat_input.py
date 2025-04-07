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
from open_webui.env import VERSION

DEFAULT_ONECALL_SUBMIT = tuple(map(int, VERSION.split("."))) >= (0, 6, 0)

class Action:
    class Valves(BaseModel):
        ONECALL_SUBMIT: bool = Field(
            default=DEFAULT_ONECALL_SUBMIT,
            description="If true, the action make submit by 1 call. Otherwise, 2 calls are made as required by prior to 0.5.20. Default true for 0.5.21+",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.actions = [
            {"id": "1-Click"},
            {"id": "Dialog"}
        ]

    async def action(
        self,
        body: dict,
        __user__=None,
        __id__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> Optional[dict]:
        print(f"action:{__name__}")
        print(body)

        content = get_last_user_message(body["messages"])

        if __id__ == 'Dialog':
            content = await __event_call__(
                {
                    "type": "input",
                    "data": {
                        "title": "modify a message",
                        "message": "here write a message to append",
                        "value": content,
                    },
                }
            )

        if content and __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "adding message", "done": False},
                }
            )
            await asyncio.sleep(1)
            content = content.replace("$", "\\$")
            if not self.valves.ONECALL_SUBMIT:
                await __event_emitter__(
                    {
                        "type": "execute",
                        "data": {"code": f'postMessage({{"type":"input:prompt", "text": String.raw`{content}`}})'}
                    } 
                )
            await __event_emitter__(
                {
                    "type": "execute",
                    "data": {"code": f'postMessage({{"type":"input:prompt:submit", "text": String.raw`{content}`}})'}
                } 
            )
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "added message", "done": True},
                }
            )
