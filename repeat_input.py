"""
title: Repeat Input Action
author: yak_ex
author_url: https://github.com/yak1ex/
git_url: https://github.com/yak1ex/open-webui-plugins.git
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9Im5vbmUiIHZpZXdCb3g9IjAgMCAyNCAyNCIgc3Ryb2tlLXdpZHRoPSIyLjMiIHN0cm9rZT0iY3VycmVudENvbG9yIiBjbGFzcz0idy00IGgtNCI+PHBhdGggaWQ9InJlZ2VuZXJhdGUiIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEyIDEyKSBzY2FsZSgwLjgpIHRyYW5zbGF0ZSgtMTggLTE4KSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBkPSJNMTYuMDIzIDkuMzQ4aDQuOTkydi0uMDAxTTIuOTg1IDE5LjY0NHYtNC45OTJtMCAwaDQuOTkybS00Ljk5MyAwbDMuMTgxIDMuMTgzYTguMjUgOC4yNSAwIDAwMTMuODAzLTMuN000LjAzMSA5Ljg2NWE4LjI1IDguMjUgMCAwMTEzLjgwMy0zLjdsMy4xODEgMy4xODJtMC00Ljk5MXY0Ljk5Ii8+PHBhdGggaWQ9ImVkaXQiIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEyIDEyKSBzY2FsZSgwLjgpIHRyYW5zbGF0ZSgtOCAtOCkiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgZD0iTTE2Ljg2MiA0LjQ4N2wxLjY4Ny0xLjY4OGExLjg3NSAxLjg3NSAwIDExMi42NTIgMi42NTJMNi44MzIgMTkuODJhNC41IDQuNSAwIDAxLTEuODk3IDEuMTNsLTIuNjg1LjguOC0yLjY4NWE0LjUgNC41IDAgMDExLjEzLTEuODk3TDE2Ljg2MyA0LjQ4N3ptMCAwTDE5LjUgNy4xMjUiLz48L3N2Zz4=
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
FRONTMATTER = dict(
    (x.strip() for x in line.strip().split(':',1)) # split to key, value
        for line in __doc__.strip().split('\n') # split to lines
)
DIALOG_ICON_URL="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGZpbGw9Im5vbmUiIHZpZXdCb3g9IjAgMCAyNCAyNCIgc3Ryb2tlLXdpZHRoPSIyLjMiIHN0cm9rZT0iY3VycmVudENvbG9yIiBjbGFzcz0idy00IGgtNCI+PHBhdGggaWQ9ImNvcHkiIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEyIDEyKSBzY2FsZSgwLjgpIHRyYW5zbGF0ZSgtMTggLTE4KSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBkPSJNMTUuNjY2IDMuODg4QTIuMjUgMi4yNSAwIDAwMTMuNSAyLjI1aC0zYy0xLjAzIDAtMS45LjY5My0yLjE2NiAxLjYzOG03LjMzMiAwYy4wNTUuMTk0LjA4NC40LjA4NC42MTJ2MGEuNzUuNzUgMCAwMS0uNzUuNzVIOWEuNzUuNzUgMCAwMS0uNzUtLjc1djBjMC0uMjEyLjAzLS40MTguMDg0LS42MTJtNy4zMzIgMGMuNjQ2LjA0OSAxLjI4OC4xMSAxLjkyNy4xODQgMS4xLjEyOCAxLjkwNyAxLjA3NyAxLjkwNyAyLjE4NVYxOS41YTIuMjUgMi4yNSAwIDAxLTIuMjUgMi4yNUg2Ljc1QTIuMjUgMi4yNSAwIDAxNC41IDE5LjVWNi4yNTdjMC0xLjEwOC44MDYtMi4wNTcgMS45MDctMi4xODVhNDguMjA4IDQ4LjIwOCAwIDAxMS45MjctLjE4NCIvPjxwYXRoIGlkPSJlZGl0IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxMiAxMikgc2NhbGUoMC44KSB0cmFuc2xhdGUoLTggLTgpIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGQ9Ik0xNi44NjIgNC40ODdsMS42ODctMS42ODhhMS44NzUgMS44NzUgMCAxMTIuNjUyIDIuNjUyTDYuODMyIDE5LjgyYTQuNSA0LjUgMCAwMS0xLjg5NyAxLjEzbC0yLjY4NS44LjgtMi42ODVhNC41IDQuNSAwIDAxMS4xMy0xLjg5N0wxNi44NjMgNC40ODd6bTAgMEwxOS41IDcuMTI1Ii8+PC9zdmc+"

class Action:
    class Valves(BaseModel):
        ONECALL_SUBMIT: bool = Field(
            default=DEFAULT_ONECALL_SUBMIT,
            description="If true, the action make submit by 1 call. Otherwise, 2 calls are made as required by prior to 0.5.20. Default true for 0.5.21+",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.actions = [
            {"id": "1-Click", "icon_url": FRONTMATTER["icon_url"]},
            {"id": "Dialog", "icon_url": DIALOG_ICON_URL }
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
