from random import randint

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ImgGen-Helper-SDWebUI")

@mcp.tool()
def dice(n: int) -> int:
    """
    Return a random integer from 1 to n (inclusive, which means n candidates).

    Args:
        n (int):  A number of faces of the dice to be thrown
    """
    return randint(1, n)


if __name__ == "__main__":
    mcp.run()
